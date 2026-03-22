"""Translation control endpoints: trigger, cancel, progress."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..repositories.project_repo import ProjectRepository
from ..repositories.block_repo import BlockRepository
from ..schemas.common import ok
from ..schemas.translate import TranslateRequest, ProgressResponse
from ..tasks.celery_app import celery_app

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["translate"])


def _parse_chapter_range(range_str: str) -> list[int]:
    """Parse '1-3' or '1,3,5' into a list of 1-based indices."""
    indices: list[int] = []
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            indices.extend(range(int(lo), int(hi) + 1))
        else:
            indices.append(int(part))
    return sorted(set(indices))


@router.post("/{project_id}/translate", summary="触发翻译")
async def start_translation(
    project_id: str,
    body: TranslateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start an async translation task for a project."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.status in ("translating",):
        raise HTTPException(
            status_code=409, detail="该项目已有翻译任务进行中",
        )

    chapter_indices = (
        _parse_chapter_range(body.chapter_range)
        if body.chapter_range else None
    )

    # Send task to Celery
    from ..tasks.translate import translate_project_task

    result = translate_project_task.delay(
        project_id=project_id,
        provider=body.provider,
        model=body.model,
        api_key=body.api_key,
        base_url=body.base_url,
        chapter_indices=chapter_indices,
    )

    # Persist task id
    project.celery_task_id = result.id
    project.status = "translating"
    project.error_message = None
    await db.commit()

    log.info("翻译任务已提交: project=%s, task=%s", project_id, result.id)
    return ok(
        {"project_id": project_id, "task_id": result.id},
        message="翻译任务已提交",
    )


@router.post("/{project_id}/cancel", summary="取消翻译")
async def cancel_translation(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a running translation task."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.status != "translating" or not project.celery_task_id:
        raise HTTPException(status_code=409, detail="没有进行中的翻译任务")

    celery_app.control.revoke(project.celery_task_id, terminate=True)

    project.status = "cancelled"
    project.celery_task_id = None
    await db.commit()

    log.info("翻译任务已取消: project=%s", project_id)
    return ok(message="翻译任务已取消")


@router.get("/{project_id}/progress", summary="翻译进度")
async def get_progress(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the current translation progress for a project."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    block_repo = BlockRepository(db)
    completed = await block_repo.count_by_status(project_id, "completed")
    total = project.total_blocks
    pct = (completed / total * 100) if total > 0 else 0.0

    resp = ProgressResponse(
        project_id=project_id,
        status=project.status,
        total_blocks=total,
        completed_blocks=completed,
        percent=round(pct, 1),
        error_message=project.error_message,
    )
    return ok(resp.model_dump())
