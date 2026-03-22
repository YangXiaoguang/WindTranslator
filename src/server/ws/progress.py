"""WebSocket endpoint for real-time translation progress.

Subscribes to Redis pub/sub channel `progress:{project_id}` and
forwards messages to the connected WebSocket client.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings

log = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/projects/{project_id}/progress")
async def ws_progress(websocket: WebSocket, project_id: str) -> None:
    """Stream translation progress events to the client.

    The client connects and receives JSON messages like:
        {"event": "progress", "data": {"blocks_done": 5, ...}}
        {"event": "completed", "data": {"output_path": "..."}}
        {"event": "error", "data": {"message": "..."}}
    """
    await websocket.accept()
    log.info("WS connected: project=%s", project_id)

    subscriber = None
    try:
        subscriber = await _subscribe(project_id)
        if subscriber is None:
            # Redis not available — fall back to polling
            await _poll_fallback(websocket, project_id)
            return

        # Read from Redis pub/sub and forward to WebSocket
        while True:
            message = await asyncio.to_thread(_get_message, subscriber, timeout=1.0)
            if message and message["type"] == "message":
                raw = message["data"]
                text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                await websocket.send_text(text)
                parsed = json.loads(text)
                if parsed.get("event") in ("completed", "error"):
                    break

            # Send heartbeat every cycle to detect dead connections
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        log.info("WS disconnected: project=%s", project_id)
    except Exception as exc:
        log.warning("WS error: project=%s, %s", project_id, exc)
    finally:
        if subscriber is not None:
            try:
                subscriber.unsubscribe()
                subscriber.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


async def _subscribe(project_id: str):
    """Subscribe to the Redis pub/sub channel. Returns None if Redis unavailable."""
    try:
        import redis as _redis

        settings = get_settings()
        r = _redis.Redis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        pubsub.subscribe(f"progress:{project_id}")
        return pubsub
    except Exception as exc:
        log.warning("Redis 不可用，WebSocket 降级为轮询: %s", exc)
        return None


def _get_message(pubsub, timeout: float = 1.0):
    """Blocking call to get a pub/sub message (runs in thread)."""
    return pubsub.get_message(timeout=timeout)


async def _poll_fallback(websocket: WebSocket, project_id: str) -> None:
    """Fallback: periodically query DB for progress when Redis is unavailable."""
    from ..database import async_session_factory
    from ..repositories.project_repo import ProjectRepository
    from ..repositories.block_repo import BlockRepository

    while True:
        try:
            async with async_session_factory() as session:
                repo = ProjectRepository(session)
                project = await repo.get_by_id(project_id)
                if project is None:
                    await websocket.send_json({
                        "event": "error",
                        "data": {"message": "项目不存在"},
                    })
                    break

                block_repo = BlockRepository(session)
                completed = await block_repo.count_by_status(project_id, "completed")
                total = project.total_blocks
                pct = completed / total * 100 if total > 0 else 0

                await websocket.send_json({
                    "event": "progress",
                    "data": {
                        "blocks_done": completed,
                        "blocks_total": total,
                        "percent": round(pct, 1),
                        "status": project.status,
                    },
                })

                if project.status in ("completed", "failed", "cancelled"):
                    event = "completed" if project.status == "completed" else "error"
                    await websocket.send_json({
                        "event": event,
                        "data": {
                            "output_path": project.output_path,
                            "message": project.error_message,
                        },
                    })
                    break

            await asyncio.sleep(2)

        except WebSocketDisconnect:
            break
        except Exception as exc:
            log.warning("Poll fallback error: %s", exc)
            await asyncio.sleep(2)
