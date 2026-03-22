"""File download endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..repositories.project_repo import ProjectRepository

router = APIRouter(prefix="/api/projects", tags=["downloads"])


@router.get("/{project_id}/download/pdf", summary="下载翻译后的 PDF")
async def download_pdf(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Download the translated PDF for a completed project."""
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.status != "completed" or not project.output_path:
        raise HTTPException(status_code=404, detail="PDF 尚未生成")

    output = Path(project.output_path)
    if not output.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在")

    return FileResponse(
        path=str(output),
        filename=f"{project.title or project.filename}_zh.pdf",
        media_type="application/pdf",
    )
