"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.request_log import RequestLogMiddleware
from .routers import projects, translate, downloads, config
from .ws.progress import router as ws_router

log = logging.getLogger(__name__)

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s %(name)s: %(message)s",
)


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown hooks."""
    log.info("WindTranslator API 启动中…")
    await init_db()
    log.info("数据库初始化完成")
    yield
    log.info("WindTranslator API 关闭")


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="WindTranslator API",
    version="0.3.0",
    description="英文 EPUB/PDF 电子书翻译为中文 PDF — REST API + WebSocket",
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost first) ──────────────────────
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLogMiddleware)
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(projects.router)
app.include_router(translate.router)
app.include_router(downloads.router)
app.include_router(config.router)
app.include_router(ws_router)


# ── Health check ─────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok", "version": "0.3.0"}
