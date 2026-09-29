import pytest
from app.core.evidence import EvidenceStore
from app.core.models import Evidence


def test_evidence_model_creation():
    ev = Evidence(
        id="E-001",
        finding="93.184.216.34",
        entity_type="IP_ADDRESS",
        source="DNS",
        source_reference="A query for example.com",
        description="A record test",
    )
    assert ev.id == "E-001"
    assert ev.finding == "93.184.216.34"
    assert ev.entity_type == "IP_ADDRESS"
    assert ev.source == "DNS"
    assert ev.source_reference == "A query for example.com"
    assert ev.collected_at != ""


def test_evidence_store_sequential_ids():
    store = EvidenceStore()
    e1 = store.add_evidence("1.1.1.1", "IP_ADDRESS", "DNS", "A query", "test")
    e2 = store.add_evidence("2.2.2.2", "IP_ADDRESS", "DNS", "A query", "test")

    assert e1.id == "E-001"
    assert e2.id == "E-002"
    assert store.count() == 2


def test_ingest_dns_results():
    mock_dns = {
        "collector": "dns",
        "target": "example.com",
        "findings": {
            "A": ["93.184.216.34"],
            "MX": ["10 mail.example.com"],
            "NS": ["ns1.example.com"],
            "TXT": [],
        },
        "errors": {},
    }

    store = EvidenceStore()
    items = store.ingest_dns_results(mock_dns)

    assert len(items) == 3
    assert items[0].id == "E-001"
    assert items[0].finding == "93.184.216.34"
    assert items[0].entity_type == "IP_ADDRESS"

    assert items[1].id == "E-002"
    assert items[1].entity_type == "MAIL_SERVER"

    assert items[2].id == "E-003"
    assert items[2].entity_type == "NAME_SERVER"
