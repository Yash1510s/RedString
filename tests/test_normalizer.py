import pytest
from app.core.evidence import EvidenceStore
from app.core.models import Evidence, Finding
from app.core.normalizer import DataNormalizer


def test_data_normalizer_single_evidence():
    ev = Evidence(
        id="E-001",
        finding="93.184.216.34",
        entity_type="IP_ADDRESS",
        source="DNS",
        source_reference="A query for example.com",
        description="A record test",
    )

    normalizer = DataNormalizer()
    findings = normalizer.normalize_evidence([ev])

    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, Finding)
    assert f.id == "FND-001"
    assert f.entity_type == "IP_ADDRESS"
    assert f.value == "93.184.216.34"
    assert f.source == "DNS"
    assert f.evidence_id == "E-001"


def test_data_normalizer_multiple_sources():
    store = EvidenceStore()
    
    # Ingest DNS
    store.ingest_dns_results({
        "collector": "dns",
        "target": "example.com",
        "findings": {"A": ["93.184.216.34"], "MX": ["mail.example.com"]},
        "errors": {},
    })

    # Ingest CT
    store.ingest_certificate_results({
        "collector": "certificate_transparency",
        "target": "example.com",
        "findings": ["api.example.com"],
        "errors": {},
    })

    # Ingest Technology
    store.ingest_technology_results({
        "collector": "technology_detection",
        "target": "example.com",
        "findings": [{"name": "nginx", "basis": "Server HTTP header"}],
        "errors": {},
    })

    normalizer = DataNormalizer()
    findings = normalizer.normalize_evidence(store.get_all())

    assert len(findings) == 4
    assert findings[0].id == "FND-001"
    assert findings[1].id == "FND-002"
    assert findings[2].id == "FND-003"
    assert findings[3].id == "FND-004"

    entity_types = [f.entity_type for f in findings]
    assert "IP_ADDRESS" in entity_types
    assert "MAIL_SERVER" in entity_types
    assert "SUBDOMAIN" in entity_types
    assert "TECHNOLOGY" in entity_types
