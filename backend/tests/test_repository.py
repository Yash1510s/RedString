"""Tests for database models, deduplication, and repository layer."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.models.normalisation import truncate_payload
from app.models.repository import InvestigationRepository
from app.models.schemas import (
    Confidence,
    EntityIn,
    EntityType,
    EvidenceIn,
    InvestigationCreate,
    RelationIn,
    RelationType,
)


@pytest.fixture
async def test_session() -> AsyncSession:
    """Provide an isolated in-memory SQLite database session for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_investigation(test_session: AsyncSession) -> None:
    repo = InvestigationRepository(test_session)
    create_dto = InvestigationCreate(
        target="  EXAMPLE.COM.  ",
        target_type="domain",
        official_domain=None,
        consent=True,
    )
    inv = await repo.create_investigation(create_dto)
    await test_session.commit()

    assert inv.id is not None
    assert inv.target == "example.com"
    assert inv.consent_given is True
    assert inv.consent_at is not None
    assert inv.status == "pending"


@pytest.mark.asyncio
async def test_upsert_duplicate_entity_merges_and_appends_evidence(
    test_session: AsyncSession,
) -> None:
    repo = InvestigationRepository(test_session)
    inv = await repo.create_investigation(
        InvestigationCreate(target="example.com", consent=True)
    )

    now = datetime.now(timezone.utc)
    ev1 = EvidenceIn(
        source_name="dns",
        source_ref="A example.com",
        raw={"ip": "93.184.216.34"},
        collected_at=now,
        collector_version="1.0.0",
    )
    entity_first = EntityIn(
        type=EntityType.ip,
        value="93.184.216.34",
        attributes={"country": "US"},
        evidence=[ev1],
    )

    # First insert
    e1 = await repo.upsert_entity(inv.id, entity_first)
    await test_session.commit()

    assert e1.id is not None
    assert e1.attributes == {"country": "US"}

    # Duplicate insert with new attribute and new evidence
    ev2 = EvidenceIn(
        source_name="ct",
        source_ref="https://crt.sh/?q=example.com",
        raw={"cert_id": 12345},
        collected_at=now,
        collector_version="1.0.0",
    )
    entity_second = EntityIn(
        type=EntityType.ip,
        value="93.184.216.34",
        attributes={"asn": "AS15133"},
        evidence=[ev2],
    )

    e2 = await repo.upsert_entity(inv.id, entity_second)
    await test_session.commit()

    # Must be the same entity ID (no duplicate row)
    assert e2.id == e1.id
    # Attributes must be merged
    assert e2.attributes == {"country": "US", "asn": "AS15133"}

    # Must have both evidence rows
    evidence_list = await repo.get_evidence_for_entity(e1.id)
    assert len(evidence_list) == 2
    sources = {ev.source_name for ev in evidence_list}
    assert sources == {"dns", "ct"}


@pytest.mark.asyncio
async def test_upsert_relation_and_evidence(test_session: AsyncSession) -> None:
    repo = InvestigationRepository(test_session)
    inv = await repo.create_investigation(
        InvestigationCreate(target="example.com", consent=True)
    )

    now = datetime.now(timezone.utc)
    ev = EvidenceIn(
        source_name="dns",
        source_ref="A example.com",
        raw={"answer": "93.184.216.34"},
        collected_at=now,
        collector_version="1.0.0",
    )

    rel_in = RelationIn(
        source=(EntityType.domain, "example.com"),
        target=(EntityType.ip, "93.184.216.34"),
        type=RelationType.RESOLVES_TO,
        confidence=Confidence.high,
        evidence=[ev],
    )

    relation = await repo.upsert_relation(inv.id, rel_in)
    await test_session.commit()

    assert relation.id is not None
    assert relation.confidence == "high"
    assert relation.type == "RESOLVES_TO"

    evidence_list = await repo.get_evidence_for_relation(relation.id)
    assert len(evidence_list) == 1
    assert evidence_list[0].relation_id == relation.id
    assert evidence_list[0].source_name == "dns"


def test_payload_truncation() -> None:
    small_payload = {"key": "value"}
    assert truncate_payload(small_payload, max_bytes=1024) == small_payload

    large_payload = {"data": "X" * 70000}
    result = truncate_payload(large_payload, max_bytes=65536)
    assert result.get("truncated") is True
    assert "original_length_bytes" in result
