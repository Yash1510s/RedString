from typing import Any, Dict, List
from app.core.models import Evidence


class EvidenceStore:
    """
    In-memory store for tracking and organizing investigation evidence provenance.
    """

    # Mapping from DNS record types to Entity types
    DNS_ENTITY_MAP = {
        "A": "IP_ADDRESS",
        "AAAA": "IP_ADDRESS",
        "MX": "MAIL_SERVER",
        "NS": "NAME_SERVER",
        "TXT": "TXT_RECORD",
        "CNAME": "CANONICAL_NAME",
    }

    def __init__(self):
        self._items: List[Evidence] = []
        self._counter: int = 1

    def add_evidence(
        self,
        finding: str,
        entity_type: str,
        source: str,
        source_reference: str,
        description: str,
    ) -> Evidence:
        """
        Adds a new evidence record with an auto-incremented ID (e.g., E-001).
        """
        evidence_id = f"E-{self._counter:03d}"
        self._counter += 1

        evidence = Evidence(
            id=evidence_id,
            finding=finding,
            entity_type=entity_type,
            source=source,
            source_reference=source_reference,
            description=description,
        )
        self._items.append(evidence)
        return evidence

    def ingest_dns_results(self, dns_data: Dict[str, Any]) -> List[Evidence]:
        """
        Transforms raw DNS findings into structured Evidence records.
        """
        target = dns_data.get("target", "")
        findings = dns_data.get("findings", {})
        added: List[Evidence] = []

        for rtype, records in findings.items():
            entity_type = self.DNS_ENTITY_MAP.get(rtype, "RECORD")
            for record in records:
                ev = self.add_evidence(
                    finding=record,
                    entity_type=entity_type,
                    source="DNS",
                    source_reference=f"{rtype} query for {target}",
                    description=f"Passive DNS {rtype} record observed for target domain '{target}'.",
                )
                added.append(ev)

        return added

    def ingest_certificate_results(self, cert_data: Dict[str, Any]) -> List[Evidence]:
        """
        Transforms Certificate Transparency hostnames into structured Evidence records.
        """
        target = cert_data.get("target", "")
        findings = cert_data.get("findings", [])
        added: List[Evidence] = []

        for hostname in findings:
            entity_type = "DOMAIN" if hostname == target else "SUBDOMAIN"
            ev = self.add_evidence(
                finding=hostname,
                entity_type=entity_type,
                source="CERTIFICATE_TRANSPARENCY",
                source_reference=f"crt.sh Certificate SAN entry for {target}",
                description=f"Publicly observable hostname '{hostname}' identified in Certificate Transparency log.",
            )
            added.append(ev)

        return added

    def get_all(self) -> List[Evidence]:
        return list(self._items)


    def count(self) -> int:
        return len(self._items)
