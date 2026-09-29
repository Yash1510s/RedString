from typing import List
from app.core.models import Finding, Relationship


class DataCorrelator:
    """
    Deterministic OSINT Correlator engine.
    Establishes explicit relationships between target domain and normalized findings.
    """

    RELATIONSHIP_MAP = {
        "SUBDOMAIN": "HAS_SUBDOMAIN",
        "IP_ADDRESS": "RESOLVES_TO",
        "TECHNOLOGY": "USES_TECHNOLOGY",
        "NAME_SERVER": "USES_NAMESERVER",
        "MAIL_SERVER": "USES_MAILSERVER",
        "CANONICAL_NAME": "HAS_CNAME",
    }

    def __init__(self):
        self._counter: int = 1

    def correlate(self, target_domain: str, findings: List[Finding]) -> List[Relationship]:
        """
        Generates deterministic relationships between target domain and normalized findings.
        """
        relationships: List[Relationship] = []

        for finding in findings:
            # Skip associating domain entity to itself
            if finding.entity_type == "DOMAIN" and finding.value.lower() == target_domain.lower():
                continue

            rel_type = self.RELATIONSHIP_MAP.get(finding.entity_type, "ASSOCIATED_WITH")
            rel_id = f"REL-{self._counter:03d}"
            self._counter += 1

            rel = Relationship(
                id=rel_id,
                source_entity=target_domain,
                relationship_type=rel_type,
                target_entity=finding.value,
                evidence_id=finding.evidence_id,
            )
            relationships.append(rel)

        return relationships
