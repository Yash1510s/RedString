"""Repository layer handling data persistence, normalization, and deduplication."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import CollectorRun, Entity, Evidence, Investigation, Relation
from app.models.normalisation import normalise_hostname, truncate_payload, utc_now
from app.models.schemas import (
    Confidence,
    EntityIn,
    EntityType,
    InvestigationCreate,
    RelationIn,
)

CONFIDENCE_RANKS = {
    Confidence.low: 1,
    Confidence.medium: 2,
    Confidence.high: 3,
}


class InvestigationRepository:
    """Handles database transactions for investigations, entities, and evidence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_investigation(self, data: InvestigationCreate) -> Investigation:
        clean_target = (
            normalise_hostname(data.target)
            if data.target_type == "domain"
            else data.target.strip()
        )
        inv = Investigation(
            target=clean_target,
            target_type=data.target_type,
            official_domain=(
                normalise_hostname(data.official_domain) if data.official_domain else None
            ),
            status="pending",
            consent_given=data.consent,
            consent_at=utc_now() if data.consent else None,
            created_at=utc_now(),
        )
        self.session.add(inv)
        await self.session.flush()
        return inv

    async def get_investigation(self, investigation_id: int) -> Investigation | None:
        """Fetch an investigation by its primary key."""
        stmt = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .options(
                selectinload(Investigation.entities),
                selectinload(Investigation.relations),
                selectinload(Investigation.collector_runs),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_entity(self, investigation_id: int, entity_in: EntityIn) -> Entity:
        """Insert a new entity or merge attributes into existing entity, appending all evidence."""
        # Normalise value based on type
        clean_value = entity_in.value.strip()
        if entity_in.type in {EntityType.domain, EntityType.subdomain, EntityType.nameserver}:
            clean_value = normalise_hostname(clean_value)

        # Check for existing entity in this investigation
        stmt = select(Entity).where(
            Entity.investigation_id == investigation_id,
            Entity.type == entity_in.type.value,
            Entity.value == clean_value,
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            # Merge attributes non-destructively
            merged_attrs = dict(entity.attributes)
            merged_attrs.update(entity_in.attributes)
            entity.attributes = merged_attrs
        else:
            entity = Entity(
                investigation_id=investigation_id,
                type=entity_in.type.value,
                value=clean_value,
                attributes=entity_in.attributes,
                first_seen=utc_now(),
            )
            self.session.add(entity)
            await self.session.flush()

        # Append all new evidence
        for ev_in in entity_in.evidence:
            evidence = Evidence(
                investigation_id=investigation_id,
                entity_id=entity.id,
                relation_id=None,
                source_name=ev_in.source_name,
                source_ref=ev_in.source_ref,
                raw=truncate_payload(ev_in.raw),
                collected_at=ev_in.collected_at,
                collector_version=ev_in.collector_version,
            )
            self.session.add(evidence)

        await self.session.flush()
        return entity

    async def upsert_relation(self, investigation_id: int, relation_in: RelationIn) -> Relation:
        """Insert or update relation edge, update confidence if higher, append evidence."""
        # Resolve or create source entity
        src_entity = await self.upsert_entity(
            investigation_id=investigation_id,
            entity_in=EntityIn(
                type=relation_in.source[0],
                value=relation_in.source[1],
                evidence=relation_in.evidence,
            ),
        )

        # Resolve or create target entity
        tgt_entity = await self.upsert_entity(
            investigation_id=investigation_id,
            entity_in=EntityIn(
                type=relation_in.target[0],
                value=relation_in.target[1],
                evidence=relation_in.evidence,
            ),
        )

        # Check for existing relation edge
        stmt = select(Relation).where(
            Relation.investigation_id == investigation_id,
            Relation.source_id == src_entity.id,
            Relation.target_id == tgt_entity.id,
            Relation.type == relation_in.type.value,
        )
        result = await self.session.execute(stmt)
        relation = result.scalar_one_or_none()

        if relation:
            # Upgrade confidence if the incoming one is higher
            current_rank = CONFIDENCE_RANKS.get(Confidence(relation.confidence), 0)
            incoming_rank = CONFIDENCE_RANKS.get(relation_in.confidence, 0)
            if incoming_rank > current_rank:
                relation.confidence = relation_in.confidence.value
        else:
            relation = Relation(
                investigation_id=investigation_id,
                source_id=src_entity.id,
                target_id=tgt_entity.id,
                type=relation_in.type.value,
                confidence=relation_in.confidence.value,
            )
            self.session.add(relation)
            await self.session.flush()

        # Append all new evidence
        for ev_in in relation_in.evidence:
            evidence = Evidence(
                investigation_id=investigation_id,
                entity_id=None,
                relation_id=relation.id,
                source_name=ev_in.source_name,
                source_ref=ev_in.source_ref,
                raw=truncate_payload(ev_in.raw),
                collected_at=ev_in.collected_at,
                collector_version=ev_in.collector_version,
            )
            self.session.add(evidence)

        await self.session.flush()
        return relation

    async def get_evidence_for_entity(self, entity_id: int) -> Sequence[Evidence]:
        """Fetch all evidence rows linked to an entity."""
        stmt = (
            select(Evidence)
            .where(Evidence.entity_id == entity_id)
            .order_by(Evidence.collected_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_evidence_for_relation(self, relation_id: int) -> Sequence[Evidence]:
        """Fetch all evidence rows linked to a relation edge."""
        stmt = (
            select(Evidence)
            .where(Evidence.relation_id == relation_id)
            .order_by(Evidence.collected_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def record_collector_run(
        self,
        investigation_id: int,
        collector: str,
        status: str,
        started_at: Any,
        finished_at: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> CollectorRun:
        """Record or update a collector run lifecycle state."""
        run = CollectorRun(
            investigation_id=investigation_id,
            collector=collector,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            error=error,
        )
        self.session.add(run)
        await self.session.flush()
        return run
