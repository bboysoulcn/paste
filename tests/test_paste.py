"""Tests for the paste service."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base, Paste
from app.database import get_db
from app.config import get_settings


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_db(test_engine):
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def client(test_db):
    """Create test client with database override."""

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns usage information."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "usage" in data


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_upload_text_paste(client):
    """Test uploading a simple text paste."""
    content = b"Hello, World!"
    response = await client.post("/", content=content)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "url" in data
    assert "raw_url" in data
    assert "delete_token" in data
    assert response.headers.get("X-Delete-Token") == data["delete_token"]


@pytest.mark.asyncio
async def test_upload_text_with_filename(client):
    """Test uploading a paste with a specific filename."""
    content = b"# Test Markdown"
    response = await client.post("/test.md", content=content)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test"
    assert data["filename"] == "test.md"


@pytest.mark.asyncio
async def test_get_paste_content(client):
    """Test retrieving a paste."""
    # First upload
    content = b"Test content"
    upload_response = await client.post("/", content=content)
    paste_id = upload_response.json()["id"]

    # Then retrieve
    response = await client.get(f"/{paste_id}")
    assert response.status_code == 200
    assert response.content == content


@pytest.mark.asyncio
async def test_get_nonexistent_paste(client):
    """Test retrieving a non-existent paste."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_paste(client):
    """Test deleting a paste."""
    # First upload
    content = b"Test content"
    upload_response = await client.post("/", content=content)
    paste_id = upload_response.json()["id"]
    delete_token = upload_response.json()["delete_token"]

    # Then delete
    response = await client.delete(
        f"/{paste_id}",
        headers={"X-Delete-Token": delete_token}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    # Verify it's deleted
    get_response = await client.get(f"/{paste_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_paste_invalid_token(client):
    """Test deleting a paste with invalid token."""
    # First upload
    content = b"Test content"
    upload_response = await client.post("/", content=content)
    paste_id = upload_response.json()["id"]

    # Try to delete with wrong token
    response = await client.delete(
        f"/{paste_id}",
        headers={"X-Delete-Token": "invalid_token"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_paste_info(client):
    """Test getting paste metadata."""
    # First upload
    content = b"Test content"
    upload_response = await client.post("/", content=content)
    paste_id = upload_response.json()["id"]

    # Get info
    response = await client.get(f"/{paste_id}/info")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == paste_id
    assert data["file_size"] == len(content)
    assert "content_type" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_empty_content(client):
    """Test uploading empty content."""
    response = await client.post("/", content=b"")
    assert response.status_code == 400
