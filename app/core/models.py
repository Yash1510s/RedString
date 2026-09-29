from datetime import datetime, timezone
import uuid
from typing import Optional
from pydantic import BaseModel, Field


class Investigation(BaseModel):
    """
    Metadata model for an OSINT investigation session.
    """
    id: str = Field(default_factory=lambda: f"INV-{uuid.uuid4().hex[:8].upper()}")
    target: str
    target_type: str = "Domain"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    status: str = "INITIALIZED"


class Evidence(BaseModel):
    """
    Evidence provenance model for tracking findings to their exact source.
    """
    id: str  # e.g. E-001
    finding: str
    entity_type: str  # e.g. IP_ADDRESS, MAIL_SERVER, NAME_SERVER, TXT_RECORD, CNAME
    source: str  # e.g. DNS
    source_reference: str  # e.g. "A record query for example.com"
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    description: str
