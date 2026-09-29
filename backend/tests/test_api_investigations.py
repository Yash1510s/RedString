"""Tests for Investigation API endpoints, consent gate, and target validation."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.orchestrator import orchestrator
from app.db import Base, get_db_session
from app.main import app


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Test client with isolated SQLite in-memory database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    orig_factory = orchestrator.session_factory
    orchestrator.session_factory = session_maker

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    orchestrator.session_factory = orig_factory
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_consent_gate_rejects_unconsented_request(async_client: AsyncClient) -> None:
    """Rule S4: API must refuse to start without consent=true."""
    response = await async_client.post(
        "/api/investigations",
        json={"target": "example.com", "consent": False},
    )
    assert response.status_code == 422
    data = response.json()
    assert "lawful" in data["detail"].lower() or "consent" in data["detail"].lower()


@pytest.mark.asyncio
async def test_ssrf_guard_rejects_ip_literal_target(async_client: AsyncClient) -> None:
    """Rule S3: API must reject IP literal targets."""
    response = await async_client.post(
        "/api/investigations",
        json={"target": "127.0.0.1", "consent": True},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ssrf_guard_rejects_localhost_target(async_client: AsyncClient) -> None:
    """Rule S3: API must reject localhost."""
    response = await async_client.post(
        "/api/investigations",
        json={"target": "localhost", "consent": True},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_and_retrieve_investigation(async_client: AsyncClient) -> None:
    """Test successful investigation creation and metadata retrieval."""
    post_res = await async_client.post(
        "/api/investigations",
        json={"target": "example.com", "consent": True},
    )
    assert post_res.status_code == 201
    created = post_res.json()
    inv_id = created["id"]
    assert created["target"] == "example.com"
    assert created["consent_given"] is True

    # Retrieve list
    list_res = await async_client.get("/api/investigations")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(item["id"] == inv_id for item in items)

    # Retrieve single
    get_res = await async_client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["id"] == inv_id
    assert details["target"] == "example.com"
