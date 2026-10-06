"""API router for investigations, findings, and live SSE streaming."""

from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.summary import generate_grounded_summary, generate_template_summary
from app.core.orchestrator import orchestrator, stream_investigation_events
from app.core.ssrf_guard import InvalidTargetError, validate_target_domain
from app.correlation.engine import CorrelationEngine
from app.db import get_db_session
from app.models.db_models import AISummary, CollectorRun, Entity, Evidence, Investigation, Relation
from app.models.normalisation import utc_now
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

    def strip_url_scheme(val: str | None) -> str:
        if not val:
            return ""
        s = val.strip()
        for scheme in ("https://", "http://", "ftp://"):
            if s.lower().startswith(scheme):
                s = s[len(scheme):]
        s = s.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        return s.strip()

    try:
        clean_target = validate_target_domain(strip_url_scheme(payload.target))
    except InvalidTargetError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Clean official domain if provided
    clean_official = None
    if payload.official_domain:
        try:
            clean_official = validate_target_domain(strip_url_scheme(payload.official_domain))
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


@router.post(
    "/demo",
    status_code=status.HTTP_201_CREATED,
    summary="Create a pre-seeded offline demo investigation",
)
async def create_demo_investigation(session: DbSession) -> dict[str, Any]:
    """Seed a synthetic, pre-correlated demo investigation visibly labelled 'Demo data'."""
    now = utc_now()
    inv = Investigation(
        target="demo-target.example (Demo Data)",
        target_type="domain",
        consent_given=True,
        status="completed",
        started_at=now,
        finished_at=now,
    )
    session.add(inv)
    await session.flush()

    # Collector runs
    collector_names = ["dns", "rdap", "ct", "tech", "github"]
    for name in collector_names:
        c_run = CollectorRun(
            investigation_id=inv.id,
            collector=name,
            status="done",
            started_at=now,
            finished_at=now,
        )
        session.add(c_run)

    # Entities
    e_root = Entity(
        investigation_id=inv.id,
        type="domain",
        value="demo-target.example",
        attributes={"apex": True, "demo": True},
        first_seen=now,
    )
    e_sub1 = Entity(
        investigation_id=inv.id,
        type="subdomain",
        value="api.demo-target.example",
        attributes={"parent": "demo-target.example", "demo": True},
        first_seen=now,
    )
    e_sub2 = Entity(
        investigation_id=inv.id,
        type="subdomain",
        value="auth.demo-target.example",
        attributes={"parent": "demo-target.example", "demo": True},
        first_seen=now,
    )
    e_ip1 = Entity(
        investigation_id=inv.id,
        type="ip",
        value="93.184.216.34",
        attributes={"cloud_provider": "Edgecast / Verizon", "asn": "AS15133"},
        first_seen=now,
    )
    e_ip2 = Entity(
        investigation_id=inv.id,
        type="ip",
        value="104.21.45.12",
        attributes={"cloud_provider": "Cloudflare", "asn": "AS13335"},
        first_seen=now,
    )
    e_ns = Entity(
        investigation_id=inv.id,
        type="nameserver",
        value="ns1.demo-target.example",
        attributes={"authoritative": True},
        first_seen=now,
    )
    e_cert = Entity(
        investigation_id=inv.id,
        type="certificate",
        value="demo-target.example SSL Certificate",
        attributes={
            "issuer": "Let's Encrypt",
            "common_name": "demo-target.example",
            "san_count": 3,
            "wildcard": False,
        },
        first_seen=now,
    )
    e_tech1 = Entity(
        investigation_id=inv.id,
        type="technology",
        value="Cloudflare CDN",
        attributes={"category": "CDN / Reverse Proxy", "confidence": "high"},
        first_seen=now,
    )
    e_tech2 = Entity(
        investigation_id=inv.id,
        type="technology",
        value="Nginx 1.24",
        attributes={"category": "Web Server", "version": "1.24.0"},
        first_seen=now,
    )
    e_repo = Entity(
        investigation_id=inv.id,
        type="repository",
        value="demo-target/client-portal",
        attributes={"language": "TypeScript", "stars": 142, "license": "MIT"},
        first_seen=now,
    )

    entities = [e_root, e_sub1, e_sub2, e_ip1, e_ip2, e_ns, e_cert, e_tech1, e_tech2, e_repo]
    for e in entities:
        session.add(e)
    await session.flush()

    # Evidence for each entity
    for e in entities:
        ev = Evidence(
            investigation_id=inv.id,
            entity_id=e.id,
            source_name="synthetic-fixture",
            source_ref=f"Demo proof for {e.value}",
            raw={"sample": True, "value": e.value, "type": e.type},
            collected_at=now,
            collector_version="1.0.0-demo",
        )
        session.add(ev)

    # Relations
    r1 = Relation(investigation_id=inv.id, source_id=e_root.id, target_id=e_ip1.id, type="RESOLVES_TO", confidence="high")
    r2 = Relation(investigation_id=inv.id, source_id=e_sub1.id, target_id=e_ip2.id, type="RESOLVES_TO", confidence="high")
    r3 = Relation(investigation_id=inv.id, source_id=e_root.id, target_id=e_ns.id, type="SERVED_BY", confidence="high")
    r4 = Relation(investigation_id=inv.id, source_id=e_root.id, target_id=e_cert.id, type="SECURED_BY", confidence="high")
    r5 = Relation(investigation_id=inv.id, source_id=e_root.id, target_id=e_tech1.id, type="USES_TECH", confidence="medium")
    r6 = Relation(investigation_id=inv.id, source_id=e_sub1.id, target_id=e_tech2.id, type="USES_TECH", confidence="high")
    r7 = Relation(investigation_id=inv.id, source_id=e_root.id, target_id=e_repo.id, type="PUBLISHED_BY", confidence="medium")

    relations = [r1, r2, r3, r4, r5, r6, r7]
    for r in relations:
        session.add(r)
    await session.flush()

    for r in relations:
        ev = Evidence(
            investigation_id=inv.id,
            relation_id=r.id,
            source_name="synthetic-fixture",
            source_ref=f"Demo relationship proof for R-{r.id}",
            raw={"relation": r.type, "source": r.source_id, "target": r.target_id},
            collected_at=now,
            collector_version="1.0.0-demo",
        )
        session.add(ev)

    # AISummary
    ai_summary = AISummary(
        investigation_id=inv.id,
        model="demo-fixture-v1",
        prompt_version="1.0.0",
        output={
            "summary": "This is an offline demo investigation targeting demo-target.example. Passive reconnaissance identified 2 active subdomains, 2 public IP addresses terminating through Cloudflare and Edgecast, valid Let's Encrypt certificates, and an open-source client portal repository.",
            "key_findings": [
                {"claim": "Apex domain resolves to 93.184.216.34 (Edgecast)", "finding_ids": [f"F-{e_root.id:06d}", f"F-{e_ip1.id:06d}"]},
                {"claim": "API subdomain routes through Cloudflare reverse proxy", "finding_ids": [f"F-{e_sub1.id:06d}", f"F-{e_ip2.id:06d}", f"F-{e_tech1.id:06d}"]},
                {"claim": "Public client portal found on GitHub", "finding_ids": [f"F-{e_repo.id:06d}"]},
            ],
            "observations": [
                {"observation": "Dual-infrastructure deployment with CDN fronting API services", "finding_ids": [f"F-{e_sub1.id:06d}", f"F-{e_tech1.id:06d}"]},
                {"observation": "Nginx web server banner exposed on API endpoints", "finding_ids": [f"F-{e_tech2.id:06d}"]},
            ],
            "next_steps": [
                "Verify Cloudflare origin certificates on backend endpoints.",
                "Review public client portal repository for outdated client SDKs.",
            ],
            "limitations": [
                "Demonstration dataset: all observed values are synthetic fixtures labelled per Rule S10.",
                "RDAP personal contacts withheld per Rule S6.",
            ],
        },
        validation_status="validated",
    )
    session.add(ai_summary)

    await session.commit()
    return {
        "id": inv.id,
        "target": inv.target,
        "status": "completed",
        "findings_count": len(entities),
    }


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

    summary_data = await generate_grounded_summary(
        inv.target, entities, counts, official_domain=inv.official_domain
    )

    # Store in database
    ai_record = AISummary(
        investigation_id=investigation_id,
        model=summary_data.get("model", "deterministic-grounded-template-v1"),
        prompt_version=summary_data.get("prompt_version", "1.0.0"),
        output=summary_data,
        validation_status="validated" if not summary_data.get("is_fallback") else "fallback",
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

    # Check current entity count to see if we should auto-regenerate
    count_stmt = select(func.count(Entity.id)).where(Entity.investigation_id == investigation_id)
    current_count = (await session.execute(count_stmt)).scalar() or 0

    if record and record.output:
        summary_text = str(record.output.get("summary", ""))
        # If the cached summary had 0 verified findings, but entities are now observed, regenerate fresh!
        if ("0 verified findings" in summary_text or len(record.output.get("key_findings", [])) == 0) and current_count > 0:
            return await create_investigation_summary(investigation_id, session)
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


