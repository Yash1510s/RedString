"""Collector Orchestrator managing collection workflows and SSE progress streaming."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from app.collectors.base import BaseCollector
from app.collectors.ct import CTCollector
from app.collectors.dns import DNSCollector
from app.collectors.github import GitHubCollector
from app.collectors.rdap import RDAPCollector
from app.collectors.tech import TechCollector
from app.db import async_session_factory
from app.models.normalisation import utc_now
from app.models.repository import InvestigationRepository

logger = logging.getLogger(__name__)


class InvestigationEventBus:
    """Pub/Sub event broadcaster for Server-Sent Events (SSE)."""

    def __init__(self) -> None:
        self._listeners: dict[int, list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, investigation_id: int) -> asyncio.Queue[dict[str, Any]]:
        """Subscribe to real-time events for an investigation."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if investigation_id not in self._listeners:
            self._listeners[investigation_id] = []
        self._listeners[investigation_id].append(queue)
        return queue

    def unsubscribe(self, investigation_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Unsubscribe from real-time events."""
        if investigation_id in self._listeners:
            self._listeners[investigation_id] = [
                q for q in self._listeners[investigation_id] if q is not queue
            ]
            if not self._listeners[investigation_id]:
                del self._listeners[investigation_id]

    async def broadcast(self, investigation_id: int, event: dict[str, Any]) -> None:
        """Broadcast an event to all active subscribers for an investigation."""
        queues = self._listeners.get(investigation_id, [])
        for q in queues:
            await q.put(event)


event_bus = InvestigationEventBus()


class Orchestrator:
    """Manages execution of passive intelligence collectors for an investigation."""

    def __init__(self, session_factory: Any = async_session_factory) -> None:
        self.session_factory = session_factory
        self.collectors: list[BaseCollector] = [
            DNSCollector(),
            RDAPCollector(),
            CTCollector(),
            TechCollector(),
            GitHubCollector(),
        ]

    async def run_investigation(self, investigation_id: int, target: str) -> None:
        """Execute all passive collectors, save findings to DB, and stream progress events."""
        async with self.session_factory() as session:
            repo = InvestigationRepository(session)
            inv = await repo.get_investigation(investigation_id)
            if not inv:
                logger.error("Investigation %d not found", investigation_id)
                return

            inv.status = "running"
            inv.started_at = utc_now()
            await session.commit()

        await event_bus.broadcast(
            investigation_id,
            {"type": "status_change", "status": "running", "timestamp": str(utc_now())},
        )

        overall_status = "completed"

        for collector in self.collectors:
            started_at = utc_now()
            await event_bus.broadcast(
                investigation_id,
                {
                    "type": "collector_start",
                    "collector": collector.name,
                    "timestamp": str(started_at),
                },
            )

            try:
                result = await collector.collect(target)

                # Persist collector run and findings in database
                async with self.session_factory() as session:
                    repo = InvestigationRepository(session)
                    finished_at = utc_now()

                    await repo.record_collector_run(
                        investigation_id=investigation_id,
                        collector=collector.name,
                        status=result.status,
                        started_at=started_at,
                        finished_at=finished_at,
                        error={"errors": [e.model_dump() for e in result.errors]}
                        if result.errors
                        else None,
                    )

                    # Persist entities and their evidence
                    for ent in result.entities:
                        await repo.upsert_entity(investigation_id, ent)

                    # Persist relations and their evidence
                    for rel in result.relations:
                        await repo.upsert_relation(investigation_id, rel)

                    await session.commit()

                await event_bus.broadcast(
                    investigation_id,
                    {
                        "type": "collector_done",
                        "collector": collector.name,
                        "status": result.status,
                        "entities_count": len(result.entities),
                        "relations_count": len(result.relations),
                        "duration_ms": result.duration_ms,
                    },
                )

                if result.status == "failed" and overall_status == "completed":
                    overall_status = "partial"

            except Exception as exc:
                logger.exception("Collector %s failed unexpectedly: %s", collector.name, exc)
                overall_status = "partial"

                async with self.session_factory() as session:
                    repo = InvestigationRepository(session)
                    await repo.record_collector_run(
                        investigation_id=investigation_id,
                        collector=collector.name,
                        status="failed",
                        started_at=started_at,
                        finished_at=utc_now(),
                        error={"message": str(exc)},
                    )
                    await session.commit()

                await event_bus.broadcast(
                    investigation_id,
                    {
                        "type": "collector_done",
                        "collector": collector.name,
                        "status": "failed",
                        "error": str(exc),
                    },
                )

        # Mark investigation completion
        async with self.session_factory() as session:
            repo = InvestigationRepository(session)
            inv = await repo.get_investigation(investigation_id)
            if inv:
                inv.status = overall_status
                inv.finished_at = utc_now()
                await session.commit()

        await event_bus.broadcast(
            investigation_id,
            {
                "type": "investigation_complete",
                "status": overall_status,
                "timestamp": str(utc_now()),
            },
        )


orchestrator = Orchestrator()


async def stream_investigation_events(investigation_id: int) -> AsyncIterator[str]:
    """Async generator yielding Server-Sent Events formatted messages."""
    queue = event_bus.subscribe(investigation_id)
    try:
        # Initial ping
        yield f"event: ping\ndata: {json.dumps({'time': str(utc_now())})}\n\n"
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "investigation_complete":
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat comment
                yield ": keep-alive\n\n"
    finally:
        event_bus.unsubscribe(investigation_id, queue)
