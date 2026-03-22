"""Project management endpoints: upload, list, detail, delete."""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..parser.epub import EPUBParserService
from ..repositories.project_repo import ProjectRepository
from ..repositories.chapter_repo import ChapterRepository
from ..schemas.common import ok
from ..schemas.project import ProjectResponse, ProjectDetail, ChapterPreview
from ..storage import save_upload, cleanup_project, MAX_UPLOAD_SIZE

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])

_SUPPORTED_EXTS = {".epub", ".pdf"}


@router.post("/upload", summary="上传电子书并解析")
async def upload_book(
    file: UploadFile = File(..., description="EPUB 或 PDF 文件"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload an ebook, parse it, and persist chapters to the database."""
    # Sanitize filename to prevent path traversal attacks
    filename = os.path.basename(file.filename or "unknown")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 {ext!r}，目前支持: {', '.join(_SUPPORTED_EXTS)}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大 ({len(content) / 1024 / 1024:.1f}MB)，"
                   f"限制 {MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB",
        )

    project_id = str(uuid.uuid4())
    filepath = save_upload(project_id, filename, content)

    try:
        parser_svc = EPUBParserService(db)
        project = await parser_svc.parse_and_persist(
            str(filepath), filename=filename,
        )
    except Exception as exc:
        cleanup_project(project_id)
        log.exception("解析失败: %s", filename)
        raise HTTPException(status_code=422, detail=f"解析失败: {exc}") from exc

    return ok(ProjectResponse.model_validate(project).model_dump())


@router.get("", summary="项目列表")
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all projects ordered by creation time."""
    repo = ProjectRepository(db)
    projects = await repo.list_all()
    items = [ProjectResponse.model_validate(p).model_dump() for p in projects]
    return ok(items)


@router.get("/{project_id}", summary="项目详情")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a project with its chapters."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id, load_chapters=True)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    chapter_repo = ChapterRepository(db)
    chapters = await chapter_repo.get_by_project(project_id)

    detail = ProjectDetail.model_validate(project)
    detail.chapters = [ChapterPreview.model_validate(ch) for ch in chapters]
    return ok(detail.model_dump())


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a project and all associated data and files."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    await repo.delete(project_id)
    await db.commit()

    cleanup_project(project_id)
    return ok(message="项目已删除")
