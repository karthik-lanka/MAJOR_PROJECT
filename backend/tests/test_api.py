"""
API tests for FastAPI endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings
from app.core.database import init_database, close_database


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Ensure database is initialized for tests."""
    settings = get_settings()
    await init_database(settings.database_url)
    yield
    # Keep database open or cleanup if needed


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "docs" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data


@pytest.mark.asyncio
async def test_api_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "gemini_configured" in data
        assert "pinecone_configured" in data
        assert "total_documents" in data


@pytest.mark.asyncio
async def test_invalid_upload_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/documents/upload",
            files={"file": ("malicious.exe", b"MZ...", "application/x-msdownload")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported file type" in data["detail"]
