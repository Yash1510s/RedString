"""Base collector protocol and abstract contract per Spec Section 6."""

from typing import Protocol

from app.models.schemas import CollectorResult


class BaseCollector(Protocol):
    """Protocol enforced for all passive intelligence collectors."""

    name: str
    version: str
    timeout_s: int

    async def collect(self, target: str) -> CollectorResult:
        """Perform collection against the given target and return unified CollectorResult."""
        ...
