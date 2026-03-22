"""Celery task: translate a project's chapters via LLM.

Progress is published to Redis pub/sub channel `progress:{project_id}`
so the WebSocket endpoint can forward it to clients in real time.
"""

from __future__ import annotations

import asyncio
import json
import logging

from .celery_app import celery_app
from ..config import get_settings
from ..database import async_session_factory
from ..repositories.project_repo import ProjectRepository
from ..translator.providers import get_provider
from ..translator.engine import TranslationEngine
from ..renderer.pdf import PDFRendererService

log = logging.getLogger(__name__)


def _publish_progress(project_id: str, event: str, data: dict) -> None:
    """Publish a progress event to Redis pub/sub."""
    try:
        import redis as _redis

        settings = get_settings()
        r = _redis.Redis.from_url(settings.redis_url)
        payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        r.publish(f"progress:{project_id}", payload)
        r.close()
    except Exception as exc:
        log.debug("Redis pub/sub unavailable: %s", exc)


@celery_app.task(
    bind=True,
    name="server.tasks.translate.translate_project_task",
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
)
def translate_project_task(
    self,
    project_id: str,
    provider: str,
    model: str,
    api_key: str,
    base_url: str | None = None,
    chapter_indices: list[int] | None = None,
) -> dict:
    """Run the full translate → render pipeline for a project.

    Args:
        project_id: DB id of the TranslationProject.
        provider: LLM provider name (anthropic, openai, ...).
        model: Model identifier.
        api_key: Plain-text API key.
        base_url: Optional custom endpoint.
        chapter_indices: Optional 1-based chapter numbers.

    Returns:
        A dict with task result metadata.
    """
    return asyncio.run(
        _run(project_id, provider, model, api_key, base_url, chapter_indices)
    )


async def _run(
    project_id: str,
    provider_name: str,
    model: str,
    api_key: str,
    base_url: str | None,
    chapter_indices: list[int] | None,
) -> dict:
    """Async implementation of the translation pipeline."""
    settings = get_settings()

    async with async_session_factory() as session:
        project_repo = ProjectRepository(session)

        # Build LLM provider
        llm_provider = get_provider(
            provider=provider_name,
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

        # Progress callback → Redis pub/sub
        def on_progress(done: int, total: int, chapter_title: str) -> None:
            pct = done / total * 100 if total else 0
            log.info(
                "进度: %d/%d (%.1f%%) — %s", done, total, pct, chapter_title,
            )
            _publish_progress(project_id, "progress", {
                "blocks_done": done,
                "blocks_total": total,
                "percent": round(pct, 1),
                "chapter_title": chapter_title,
            })

        try:
            # Notify start
            _publish_progress(project_id, "started", {
                "provider": provider_name, "model": model,
            })

            # Translate
            engine = TranslationEngine(
                session=session,
                provider=llm_provider,
                on_progress=on_progress,
            )
            await engine.translate_project(project_id, chapter_indices)

            # Render PDF
            from ..storage import get_output_dir

            output_dir = get_output_dir(project_id)
            output_path = str(output_dir / f"{project_id}.pdf")
            renderer = PDFRendererService(session)
            final_path = await renderer.render(
                project_id, output_path, chapter_indices,
            )

            await project_repo.update_status(
                project_id, "completed", output_path=final_path,
            )
            await session.commit()

            _publish_progress(project_id, "completed", {
                "output_path": final_path,
            })
            return {"status": "completed", "output_path": final_path}

        except Exception as exc:
            await project_repo.update_status(
                project_id, "failed", error_message=str(exc),
            )
            await session.commit()

            _publish_progress(project_id, "error", {
                "message": str(exc),
            })
            raise
