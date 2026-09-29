from typing import List
from app.core.models import Evidence, Finding


class DataNormalizer:
    """
    Normalizes raw evidence collected from disparate OSINT collectors into
    a unified, standard Finding entity schema.
    """

    def __init__(self):
        self._counter: int = 1

    def normalize_evidence(self, evidence_list: List[Evidence]) -> List[Finding]:
        """
        Transforms a list of Evidence records into normalized Finding objects.
        """
        normalized_findings: List[Finding] = []

        for ev in evidence_list:
            finding_id = f"FND-{self._counter:03d}"
            self._counter += 1

            # Clean and normalize value string
            value_clean = ev.finding.strip()

            finding = Finding(
                id=finding_id,
                entity_type=ev.entity_type,
                value=value_clean,
                source=ev.source,
                evidence_id=ev.id,
                collected_at=ev.collected_at,
            )
            normalized_findings.append(finding)

        return normalized_findings
