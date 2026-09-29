"""SQLAlchemy 2.0 ORM models per Spec Section 5.3."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.normalisation import utc_now


class Investigation(Base):
    """Investigation execution run targeting a domain or organization."""

    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, default="domain")
    official_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    entities: Mapped[list["Entity"]] = relationship(
        "Entity", back_populates="investigation", cascade="all, delete-orphan"
    )
    relations: Mapped[list["Relation"]] = relationship(
        "Relation", back_populates="investigation", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="investigation", cascade="all, delete-orphan"
    )
    collector_runs: Mapped[list["CollectorRun"]] = relationship(
        "CollectorRun", back_populates="investigation", cascade="all, delete-orphan"
    )
    ai_summaries: Mapped[list["AISummary"]] = relationship(
        "AISummary", back_populates="investigation", cascade="all, delete-orphan"
    )


class Entity(Base):
    """Discovered entity node in the intelligence graph."""

    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="entities"
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="entity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "investigation_id", "type", "value", name="uq_entity_investigation_type_val"
        ),
        Index("ix_entity_inv_type_val", "investigation_id", "type", "value"),
    )


class Relation(Base):
    """Typed relationship edge connecting two entities."""

    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="relations"
    )
    source: Mapped["Entity"] = relationship("Entity", foreign_keys=[source_id])
    target: Mapped["Entity"] = relationship("Entity", foreign_keys=[target_id])
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="relation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "investigation_id", "source_id", "target_id", "type", name="uq_relation_edge"
        ),
        Index("ix_relation_endpoints", "investigation_id", "source_id", "target_id"),
    )


class Evidence(Base):
    """Immutable audit record providing proof for an entity or relation finding."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=True, index=True
    )
    relation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("relations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collector_version: Mapped[str] = mapped_column(String(50), nullable=False)

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="evidence"
    )
    entity: Mapped["Entity | None"] = relationship("Entity", back_populates="evidence")
    relation: Mapped["Relation | None"] = relationship("Relation", back_populates="evidence")

    __table_args__ = (
        CheckConstraint(
            "entity_id IS NOT NULL OR relation_id IS NOT NULL",
            name="ck_evidence_has_target",
        ),
    )


class CollectorRun(Base):
    """Status record of a collector run execution."""

    __tablename__ = "collector_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collector: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="collector_runs"
    )


class AISummary(Base):
    """Grounded AI or template summary produced for an investigation."""

    __tablename__ = "ai_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    investigation: Mapped["Investigation"] = relationship(
        "Investigation", back_populates="ai_summaries"
    )


class HttpCache(Base):
    """Local cache for passive upstream responses."""

    __tablename__ = "http_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=86400)
