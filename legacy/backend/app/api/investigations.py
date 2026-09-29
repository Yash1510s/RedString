"""API router for investigations, findings, and live SSE streaming."""

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.summary import generate_template_summary
from app.core.orchestrator import orchestrator, stream_investigation_events
from app.core.ssrf_guard import InvalidTargetError, validate_target_domain
from app.correlation.engine import CorrelationEngine
from app.db import get_db_session
from app.models.db_models import AISummary, Entity, Evidence, Investigation, Relation
from app.models.repository import InvestigationRepository
from app.models.schemas import InvestigationCreate, InvestigationRead
from app.reporting.report_generator import generate_html_report

router = APIRouter(prefix="/investigations", tags=["investigations"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create and start a new investigation",
)
async def create_investigation(
    payload: InvestigationCreate,
    background_tasks: BackgroundTasks,
    session: DbSession,
) -> Investigation:
    """Create and trigger an investigation.

    Enforces:
    - Consent verification (Rule S4)
    - Strict SSRF target domain validation (Rule S3)
    """
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Investigation requires explicit confirmation of lawful purpose.",
        )

    try:
        clean_target = validate_target_domain(payload.target)
    except InvalidTargetError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Clean official domain if provided
    clean_official = None
    if payload.official_domain:
        try:
            clean_official = validate_target_domain(payload.official_domain)
        except InvalidTargetError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Official domain invalid: {exc}",
            ) from exc

    repo = InvestigationRepository(session)
    inv_data = InvestigationCreate(
        target=clean_target,
        target_type=payload.target_type,
        official_domain=clean_official,
        consent=True,
    )
    inv = await repo.create_investigation(inv_data)
    await session.commit()
    await session.refresh(inv)

    # Launch background collection
    background_tasks.add_task(orchestrator.run_investigation, inv.id, clean_target)

    return inv


@router.get("", summary="List recent investigations")
async def list_investigations(
    session: DbSession,
    limit: Annotated[int, Query(le=100)] = 20,
) -> list[dict[str, Any]]:
    """List recent investigations with finding counts."""
    stmt = (
        select(
            Investigation,
            func.count(Entity.id).label("entities_count"),
        )
        .outerjoin(Entity, Entity.investigation_id == Investigation.id)
        .group_by(Investigation.id)
        .order_by(Investigation.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    items = []
    for inv, count in rows:
        items.append(
            {
                "id": inv.id,
                "target": inv.target,
                "target_type": inv.target_type,
                "status": inv.status,
                "created_at": inv.created_at.isoformat(),
                "started_at": inv.started_at.isoformat() if inv.started_at else None,
                "finished_at": inv.finished_at.isoformat() if inv.finished_at else None,
                "findings_count": count,
            }
        )
    return items


@router.get("/{investigation_id}", summary="Get investigation details and collector statuses")
async def get_investigation_details(
    investigation_id: int,
    session: DbSession,
) -> dict[str, Any]:
    """Retrieve metadata and status of collector runs for an investigation."""
    stmt = (
        select(Investigation)
        .where(Investigation.id == investigation_id)
        .options(selectinload(Investigation.collector_runs))
    )
    result = await session.execute(stmt)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )

    # Count entities
    count_stmt = select(func.count(Entity.id)).where(Entity.investigation_id == investigation_id)
    entity_count = (await session.execute(count_stmt)).scalar() or 0

    return {
        "id": inv.id,
        "target": inv.target,
        "target_type": inv.target_type,
        "official_domain": inv.official_domain,
        "status": inv.status,
        "consent_given": inv.consent_given,
        "created_at": inv.created_at.isoformat(),
        "started_at": inv.started_at.isoformat() if inv.started_at else None,
        "finished_at": inv.finished_at.isoformat() if inv.finished_at else None,
        "findings_count": entity_count,
        "collectors": [
            {
                "collector": cr.collector,
                "status": cr.status,
                "started_at": cr.started_at.isoformat(),
                "finished_at": cr.finished_at.isoformat() if cr.finished_at else None,
                "error": cr.error,
            }
            for cr in inv.collector_runs
        ],
    }


@router.get("/{investigation_id}/events", summary="Stream live progress events via SSE")
async def stream_events(investigation_id: int) -> StreamingResponse:
    """Server-Sent Events endpoint streaming collector milestones."""
    return StreamingResponse(
        stream_investigation_events(investigation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{investigation_id}/findings", summary="List findings and evidence references")
async def list_findings(
    investigation_id: int,
    session: DbSession,
) -> list[dict[str, Any]]:
    """Fetch all findings with attached evidence count and metadata."""
    stmt = (
        select(Entity)
        .where(Entity.investigation_id == investigation_id)
        .options(selectinload(Entity.evidence))
        .order_by(Entity.type, Entity.value)
    )
    result = await session.execute(stmt)
    entities = result.scalars().all()

    findings: list[dict[str, Any]] = []
    for ent in entities:
        # Determine confidence
        confidence = "high"
        sources = list({ev.source_name for ev in ent.evidence})
        findings.append(
            {
                "finding_id": f"F-{ent.id:06d}",
                "entity_id": ent.id,
                "type": ent.type,
                "value": ent.value,
                "confidence": confidence,
                "attributes": ent.attributes,
                "sources": sources,
                "evidence_count": len(ent.evidence),
                "first_seen": ent.first_seen.isoformat(),
            }
        )

    return findings


@router.get(
    "/{investigation_id}/entities/{entity_id}/evidence",
    summary="Get raw evidence for an entity",
)
async def get_entity_evidence(
    investigation_id: int,
    entity_id: int,
    session: DbSession,
) -> list[dict[str, Any]]:
    """Retrieve raw provenance records supporting a specific entity finding."""
    stmt = (
        select(Evidence)
        .where(
            Evidence.investigation_id == investigation_id,
            Evidence.entity_id == entity_id,
        )
        .order_by(Evidence.collected_at)
    )
    result = await session.execute(stmt)
    evidence_rows = result.scalars().all()

    return [
        {
            "id": ev.id,
            "source_name": ev.source_name,
            "source_ref": ev.source_ref,
            "raw": ev.raw,
            "collected_at": ev.collected_at.isoformat(),
            "collector_version": ev.collector_version,
        }
        for ev in evidence_rows
    ]


@router.get("/{investigation_id}/graph", summary="Get Cytoscape-compatible relationship graph")
async def get_investigation_graph(
    investigation_id: int,
    session: DbSession,
    types: Annotated[str | None, Query(description="Comma-separated entity types to filter")] = None,
) -> dict[str, Any]:
    """Retrieve correlated Cytoscape nodes and edges with provenance and confidence."""
    # 1. Fetch all entities for this investigation
    ent_stmt = select(Entity).where(Entity.investigation_id == investigation_id)
    if types:
        filter_types = [t.strip().lower() for t in types.split(",") if t.strip()]
        if filter_types:
            ent_stmt = ent_stmt.where(Entity.type.in_(filter_types))

    ent_res = await session.execute(ent_stmt)
    entities = list(ent_res.scalars().all())

    # 2. Fetch all relations
    rel_stmt = (
        select(Relation)
        .where(Relation.investigation_id == investigation_id)
        .options(selectinload(Relation.source), selectinload(Relation.target))
    )
    rel_res = await session.execute(rel_stmt)
    relations = list(rel_res.scalars().all())

    # 3. Fetch evidence
    ev_stmt = select(Evidence).where(Evidence.investigation_id == investigation_id)
    ev_res = await session.execute(ev_stmt)
    evidences = list(ev_res.scalars().all())

    # 4. Run correlation engine
    engine = CorrelationEngine()
    graph_data = engine.correlate(entities, relations, evidences)
    return graph_data


@router.post("/{investigation_id}/cancel", summary="Cancel a running investigation")
async def cancel_investigation(
    investigation_id: int,
    session: DbSession,
) -> dict[str, str]:
    """Cooperatively cancel a running investigation."""
    inv = await session.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if inv.status in {"pending", "running"}:
        inv.status = "cancelled"
        await session.commit()
    return {"status": "cancelled", "message": f"Investigation {investigation_id} cancelled"}


@router.delete("/{investigation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete investigation")
async def delete_investigation(
    investigation_id: int,
    session: DbSession,
) -> None:
    """Permanently delete an investigation and all associated findings (privacy control)."""
    inv = await session.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    await session.delete(inv)
    await session.commit()


@router.post("/{investigation_id}/summary", summary="Generate or regenerate AI/grounded summary")
async def create_investigation_summary(
    investigation_id: int,
    session: DbSession,
) -> dict[str, Any]:
    """Generate deterministic or AI-grounded investigation summary with citations."""
    inv = await session.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    # Fetch entities
    ent_stmt = select(Entity).where(Entity.investigation_id == investigation_id)
    ent_res = await session.execute(ent_stmt)
    entities = list(ent_res.scalars().all())

    # Calculate counts
    counts: dict[str, int] = defaultdict(int)
    for e in entities:
        counts[e.type] += 1

    summary_data = generate_template_summary(inv.target, entities, counts)

    # Store in database
    ai_record = AISummary(
        investigation_id=investigation_id,
        model="deterministic-grounded-template-v1",
        prompt_version="1.0.0",
        output=summary_data,
        validation_status="validated",
    )
    session.add(ai_record)
    await session.commit()

    return summary_data


@router.get("/{investigation_id}/summary", summary="Get latest validated summary")
async def get_investigation_summary(
    investigation_id: int,
    session: DbSession,
) -> dict[str, Any]:
    """Retrieve the latest validated summary or generate deterministic fallback."""
    stmt = (
        select(AISummary)
        .where(AISummary.investigation_id == investigation_id)
        .order_by(AISummary.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    record = res.scalar_one_or_none()
    if record and record.output:
        return record.output

    # If not generated yet, generate template on the fly
    return await create_investigation_summary(investigation_id, session)


@router.get("/{investigation_id}/report", summary="Render audit-ready printable report")
async def get_investigation_report(
    investigation_id: int,
    session: DbSession,
) -> HTMLResponse:
    """Render self-contained HTML report with all 13 sections per Spec Section 12."""
    inv = await session.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    # Fetch entities, relations, evidence
    ent_stmt = select(Entity).where(Entity.investigation_id == investigation_id)
    entities = list((await session.execute(ent_stmt)).scalars().all())

    rel_stmt = (
        select(Relation)
        .where(Relation.investigation_id == investigation_id)
        .options(selectinload(Relation.source), selectinload(Relation.target))
    )
    relations = list((await session.execute(rel_stmt)).scalars().all())

    ev_stmt = select(Evidence).where(Evidence.investigation_id == investigation_id)
    evidences = list((await session.execute(ev_stmt)).scalars().all())

    # Get or generate summary
    summary_stmt = (
        select(AISummary)
        .where(AISummary.investigation_id == investigation_id)
        .order_by(AISummary.created_at.desc())
        .limit(1)
    )
    summary_rec = (await session.execute(summary_stmt)).scalar_one_or_none()
    if summary_rec and summary_rec.output:
        summary_data = summary_rec.output
    else:
        counts: dict[str, int] = defaultdict(int)
        for e in entities:
            counts[e.type] += 1
        summary_data = generate_template_summary(inv.target, entities, counts)

    report_html = generate_html_report(inv, entities, relations, evidences, summary_data)
    return HTMLResponse(content=report_html, status_code=200)


