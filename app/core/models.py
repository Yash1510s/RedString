from datetime import datetime, timezone
import uuid
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
