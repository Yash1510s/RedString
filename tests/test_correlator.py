import pytest
from app.core.correlator import DataCorrelator
from app.core.models import Finding, Relationship


def test_correlator_mapping():
    findings = [
        Finding(id="FND-001", entity_type="DOMAIN", value="example.com", source="DNS", evidence_id="E-001"),
        Finding(id="FND-002", entity_type="SUBDOMAIN", value="api.example.com", source="CT", evidence_id="E-002"),
        Finding(id="FND-003", entity_type="IP_ADDRESS", value="93.184.216.34", source="DNS", evidence_id="E-003"),
        Finding(id="FND-004", entity_type="MAIL_SERVER", value="mail.example.com", source="DNS", evidence_id="E-004"),
        Finding(id="FND-005", entity_type="NAME_SERVER", value="ns1.example.com", source="DNS", evidence_id="E-005"),
        Finding(id="FND-006", entity_type="TECHNOLOGY", value="nginx", source="HTTP", evidence_id="E-006"),
    ]

    correlator = DataCorrelator()
    rels = correlator.correlate("example.com", findings)

    # Note: FND-001 (domain example.com) is skipped because it's target domain self-reference
    assert len(rels) == 5

    assert rels[0].id == "REL-001"
    assert rels[0].relationship_type == "HAS_SUBDOMAIN"
    assert rels[0].target_entity == "api.example.com"
    assert rels[0].evidence_id == "E-002"

    assert rels[1].relationship_type == "RESOLVES_TO"
    assert rels[1].target_entity == "93.184.216.34"

    assert rels[2].relationship_type == "USES_MAILSERVER"
    assert rels[2].target_entity == "mail.example.com"

    assert rels[3].relationship_type == "USES_NAMESERVER"
    assert rels[3].target_entity == "ns1.example.com"

    assert rels[4].relationship_type == "USES_TECHNOLOGY"
    assert rels[4].target_entity == "nginx"
