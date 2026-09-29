import pytest
from app.core.evidence import EvidenceStore
from app.core.models import Finding, Investigation, Relationship
from app.cli.interface import print_investigation_summary


def test_investigation_summary_execution():
    inv = Investigation(target="example.com")
    statuses = {
        "DNS Intelligence": "COMPLETE",
        "Certificate Transparency": "COMPLETE",
        "Technology Detection": "COMPLETE",
    }

    store = EvidenceStore()
    store.add_evidence("1.1.1.1", "IP_ADDRESS", "DNS", "A query", "test")

    findings = [
        Finding(id="FND-001", entity_type="SUBDOMAIN", value="sub.example.com", source="CT", evidence_id="E-001"),
        Finding(id="FND-002", entity_type="TECHNOLOGY", value="nginx", source="HTTP", evidence_id="E-002"),
    ]

    relationships = [
        Relationship(id="REL-001", source_entity="example.com", relationship_type="HAS_SUBDOMAIN", target_entity="sub.example.com", evidence_id="E-001"),
    ]

    # Test rendering without errors
    try:
        print_investigation_summary(inv, statuses, store, findings, relationships)
    except Exception as e:
        pytest.fail(f"print_investigation_summary raised an exception: {e}")
