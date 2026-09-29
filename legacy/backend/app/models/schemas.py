"""Authoritative Pydantic schemas for data contracts."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Supported entity categories."""

    domain = "domain"
    subdomain = "subdomain"
    ip = "ip"
    certificate = "certificate"
    technology = "technology"
    organization = "organization"
    repository = "repository"
    nameserver = "nameserver"
    mail_provider = "mail_provider"
    cloud_provider = "cloud_provider"
    person = "person"


class RelationType(str, Enum):
    """Typed relationship edges between entities."""

    HAS_SUBDOMAIN = "HAS_SUBDOMAIN"
    RESOLVES_TO = "RESOLVES_TO"
    HOSTED_ON = "HOSTED_ON"
    COVERS = "COVERS"
    USES_TECH = "USES_TECH"
    USES_NS = "USES_NS"
    USES_MAIL = "USES_MAIL"
    OWNS = "OWNS"
    MENTIONS = "MENTIONS"
    CONTRIBUTED_TO = "CONTRIBUTED_TO"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"


class Confidence(str, Enum):
    """Confidence levels for inferred or observed relationships."""

    high = "high"
    medium = "medium"
    low = "low"


class InvestigationStatus(str, Enum):
    """Investigation lifecycle statuses."""

    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class EvidenceIn(BaseModel):
    """Raw provenance evidence validating an entity or relationship finding."""

    source_name: str  # "dns", "crt.sh", "rdap", "http", "github"
    source_ref: str | None = None  # URL or query string
    raw: dict[str, Any]  # untouched payload (size-capped)
    collected_at: datetime  # UTC
    collector_version: str


class EntityIn(BaseModel):
    """Normalized entity observed during collection."""

    type: EntityType
    value: str  # normalised: lowercase, no trailing dot
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceIn] = Field(..., min_length=1)


class RelationIn(BaseModel):
    """Typed relationship discovered between two entities."""

    source: tuple[EntityType, str]
    target: tuple[EntityType, str]
    type: RelationType
    confidence: Confidence
    evidence: list[EvidenceIn] = Field(..., min_length=1)


class CollectorError(BaseModel):
    """Structured error emitted by a collector."""

    code: str  # "timeout", "rate_limited", "blocked_by_guard", "upstream_error"
    message: str
    retryable: bool


class CollectorResult(BaseModel):
    """Unified result container returned by all collectors."""

    collector: str
    status: str  # "ok" | "partial" | "failed"
    entities: list[EntityIn] = []
    relations: list[RelationIn] = []
    errors: list[CollectorError] = []
    duration_ms: int


class InvestigationCreate(BaseModel):
    """Payload to initiate a new investigation."""

    target: str
    target_type: str = "domain"
    official_domain: str | None = None
    consent: bool


class InvestigationRead(BaseModel):
    """Investigation response representation."""

    id: int
    target: str
    target_type: str
    official_domain: str | None
    status: InvestigationStatus
    consent_given: bool
    consent_at: datetime | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)
