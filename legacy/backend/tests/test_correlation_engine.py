"""Tests for Correlation Engine and Cytoscape Graph Generation."""

from datetime import datetime, timezone

from app.correlation.engine import CorrelationEngine, elevate_confidence
from app.models.db_models import Entity, Evidence, Relation


def test_elevate_confidence():
    assert elevate_confidence("low", 1) == "low"
    assert elevate_confidence("low", 2) == "medium"
    assert elevate_confidence("medium", 2) == "high"
    assert elevate_confidence("high", 3) == "high"


def test_correlation_engine_idempotent_and_structure():
    engine = CorrelationEngine()
    now = datetime.now(timezone.utc)

    e1 = Entity(id=1, investigation_id=1, type="domain", value="example.com", attributes={}, first_seen=now)
    e2 = Entity(id=2, investigation_id=1, type="subdomain", value="api.example.com", attributes={}, first_seen=now)
    e3 = Entity(id=3, investigation_id=1, type="subdomain", value="app.example.com", attributes={}, first_seen=now)
    e4 = Entity(id=4, investigation_id=1, type="ip", value="93.184.216.34", attributes={}, first_seen=now)

    r1 = Relation(id=1, investigation_id=1, source_id=1, target_id=2, type="HAS_SUBDOMAIN", confidence="medium")
    r2 = Relation(id=2, investigation_id=1, source_id=2, target_id=4, type="RESOLVES_TO", confidence="high")
    r3 = Relation(id=3, investigation_id=1, source_id=3, target_id=4, type="RESOLVES_TO", confidence="high")

    r1.source = e1
    r1.target = e2
    r2.source = e2
    r2.target = e4
    r3.source = e3
    r3.target = e4

    ev1 = Evidence(id=1, investigation_id=1, relation_id=1, source_name="ct", collected_at=now, collector_version="1.0")
    ev2 = Evidence(id=2, investigation_id=1, relation_id=1, source_name="dns", collected_at=now, collector_version="1.0")

    entities = [e1, e2, e3, e4]
    relations = [r1, r2, r3]
    evidences = [ev1, ev2]

    res1 = engine.correlate(entities, relations, evidences)
    res2 = engine.correlate(entities, relations, evidences)

    # Idempotent verification
    assert res1["meta"]["nodeCount"] == res2["meta"]["nodeCount"] == 4
    assert res1["meta"]["edgeCount"] == res2["meta"]["edgeCount"] == 3

    # Check elevated confidence on r1 (sources: ct + dns -> medium elevated to high)
    edge1 = next(e for e in res1["edges"] if e["data"]["id"] == "r1")
    assert edge1["data"]["confidence"] == "high"

    # Check shared IP group tagged on api.example.com and app.example.com
    node_api = next(n for n in res1["nodes"] if n["data"]["label"] == "api.example.com")
    node_app = next(n for n in res1["nodes"] if n["data"]["label"] == "app.example.com")
    assert "shared_ip_group" in node_api["data"]["attributes"]
    assert "shared_ip_group" in node_app["data"]["attributes"]
    assert node_api["data"]["attributes"]["shared_ip_group"] == node_app["data"]["attributes"]["shared_ip_group"]
