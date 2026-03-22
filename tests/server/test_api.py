"""Tests for REST API endpoints using FastAPI TestClient."""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from server.main import app
from server.database import Base
from server.dependencies import get_db
from server.models import TranslationProject, Chapter, ContentBlock


# ── Test database setup ──────────────────────────────────────────────

@pytest.fixture
async def test_engine():
    """Create an in-memory SQLite engine."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Yield a test session."""
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with factory() as sess:
        yield sess


@pytest.fixture
async def client(test_engine):
    """AsyncClient with overridden DB dependency."""
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    async def _override_db():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Seed helper ──────────────────────────────────────────────────────

async def _seed_project(session: AsyncSession) -> TranslationProject:
    """Insert a parsed project with one chapter and two blocks."""
    project = TranslationProject(
        filename="test.epub", file_path="/tmp/test.epub",
        format="epub", title="Test Book", status="parsed",
        total_chapters=1, total_blocks=2,
    )
    session.add(project)
    await session.flush()

    chapter = Chapter(
        project_id=project.id, index=1, title="Ch1",
        block_count=2, status="pending",
    )
    session.add(chapter)
    await session.flush()

    session.add_all([
        ContentBlock(
            chapter_id=chapter.id, index=0, block_type="h1",
            text="Ch1", status="pending",
        ),
        ContentBlock(
            chapter_id=chapter.id, index=1, block_type="p",
            text="Body text.", status="pending",
        ),
    ])
    await session.commit()
    return project


# ── Tests ────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestProjectsEndpoints:
    @pytest.mark.asyncio
    async def test_list_projects_empty(self, client):
        resp = await client.get("/api/projects")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"] == []

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_format(self, client):
        resp = await client.post(
            "/api/projects/upload",
            files={"file": ("book.docx", b"fake content", "application/octet-stream")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_file(self, client):
        big = b"x" * (51 * 1024 * 1024)  # 51 MB
        resp = await client.post(
            "/api/projects/upload",
            files={"file": ("book.epub", big, "application/epub+zip")},
        )
        assert resp.status_code == 413

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client):
        resp = await client.get("/api/projects/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client):
        resp = await client.delete("/api/projects/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_parse_and_list(self, client):
        """Upload a valid file (mocked parser) and verify it appears in the list."""
        from epub_translator.models import Chapter as EngCh, ContentBlock as EngBlk

        mock_chapters = [
            EngCh(title="Intro", blocks=[
                EngBlk(block_type="h1", text="Intro"),
                EngBlk(block_type="p", text="Body text here."),
            ])
        ]

        with patch(
            "server.parser.epub.EPUBParserService._extract",
            return_value=("Mock Book", mock_chapters),
        ):
            resp = await client.post(
                "/api/projects/upload",
                files={"file": ("book.epub", b"PK\x03\x04fake", "application/epub+zip")},
            )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "Mock Book"
        assert data["total_chapters"] == 1
        project_id = data["id"]

        # Verify list
        resp = await client.get("/api/projects")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["id"] == project_id

        # Verify detail
        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert len(detail["chapters"]) == 1

        # Delete
        resp = await client.delete(f"/api/projects/{project_id}")
        assert resp.status_code == 200

        # Confirm deleted
        resp = await client.get(f"/api/projects/{project_id}")
        assert resp.status_code == 404


class TestConfigEndpoints:
    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        resp = await client.get("/api/config/providers")
        assert resp.status_code == 200
        providers = resp.json()["data"]
        assert "anthropic" in providers
        assert "openai" in providers


class TestProgressEndpoint:
    @pytest.mark.asyncio
    async def test_progress_not_found(self, client):
        resp = await client.get("/api/projects/nonexistent/progress")
        assert resp.status_code == 404
