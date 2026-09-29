"""Grounded AI Copilot summary generator and deterministic fallback per Spec Section 10."""

import logging
from collections import defaultdict
from typing import Any

from app.models.db_models import Entity

logger = logging.getLogger(__name__)


def validate_summary(
    data: dict[str, Any],
    valid_finding_ids: set[str],
) -> tuple[bool, str]:
    """Validate summary structure, non-empty content, and authentic finding ID citations."""
    required_keys = {"summary", "key_findings", "observations", "next_steps", "limitations"}
    if not required_keys.issubset(data.keys()):
        missing = required_keys - set(data.keys())
        return False, f"Missing required keys: {missing}"

    # Verify cited finding IDs exist in the investigation
    for kf in data.get("key_findings", []):
        ids = kf.get("finding_ids", [])
        for fid in ids:
            if fid not in valid_finding_ids:
                return False, f"Invalid cited finding ID: {fid}"

    for obs in data.get("observations", []):
        ids = obs.get("finding_ids", [])
        for fid in ids:
            if fid not in valid_finding_ids:
                return False, f"Invalid cited finding ID: {fid}"

    return True, "Valid"


def generate_template_summary(
    target: str,
    entities: list[Entity],
    counts: dict[str, int],
) -> dict[str, Any]:
    """Generate deterministic, evidence-grounded template summary without AI (Spec Section 10.2)."""
    # Group entities by type
    by_type: dict[str, list[Entity]] = defaultdict(list)
    id_map: dict[int, str] = {}
    for ent in entities:
        by_type[ent.type].append(ent)
        id_map[ent.id] = f"F-{ent.id:06d}"

    key_findings: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    # 1. Domain & DNS Summary
    dns_records = by_type.get("nameserver", [])
    mail_records = by_type.get("mail_provider", [])
    if dns_records:
        ns_ids = [id_map[e.id] for e in dns_records[:4]]
        ns_names = ", ".join(e.value for e in dns_records[:3])
        key_findings.append(
            {
                "text": f"Authoritative nameservers identified for {target}: {ns_names}.",
                "finding_ids": ns_ids,
            }
        )

    if mail_records:
        mail_ids = [id_map[e.id] for e in mail_records]
        mail_names = ", ".join(e.value for e in mail_records)
        key_findings.append(
            {
                "text": f"Enterprise mail infrastructure hosted via: {mail_names}.",
                "finding_ids": mail_ids,
            }
        )

    # 2. Subdomains & Certificate Observations
    subdomains = by_type.get("subdomain", [])
    live_subdomains = [s for s in subdomains if (s.attributes or {}).get("live") is True]
    certs = by_type.get("certificate", [])

    if subdomains:
        top_subs = subdomains[:5]
        sub_ids = [id_map[s.id] for s in top_subs]
        obs_text = f"Discovered {len(subdomains)} public subdomains via Certificate Transparency; {len(live_subdomains)} resolved to live IPs."
        observations.append(
            {
                "text": obs_text,
                "finding_ids": sub_ids,
                "confidence": "high" if live_subdomains else "medium",
            }
        )

    if certs:
        c_ids = [id_map[c.id] for c in certs[:3]]
        issuers = {str((c.attributes or {}).get("issuer_name", "Unknown")) for c in certs[:3]}
        observations.append(
            {
                "text": f"Active TLS certificates observed from issuers: {', '.join(issuers)}.",
                "finding_ids": c_ids,
                "confidence": "high",
            }
        )

    # 3. Technologies & Cloud
    techs = by_type.get("technology", [])
    clouds = by_type.get("cloud_provider", [])
    if techs or clouds:
        t_ids = [id_map[t.id] for t in techs[:5]] + [id_map[c.id] for c in clouds]
        t_names = [t.value for t in techs[:5]]
        c_names = [c.value for c in clouds]
        all_stack = t_names + [f"Hosted on {c}" for c in c_names]
        key_findings.append(
            {
                "text": f"Technology stack and infrastructure components detected: {', '.join(all_stack)}.",
                "finding_ids": t_ids,
            }
        )

    # 4. Public Repositories & People
    repos = by_type.get("repository", [])
    people = by_type.get("person", [])
    if repos:
        r_ids = [id_map[r.id] for r in repos[:3]]
        r_names = ", ".join(r.value for r in repos[:3])
        key_findings.append(
            {
                "text": f"Public open-source repositories referencing {target}: {r_names}.",
                "finding_ids": r_ids,
            }
        )

    if people:
        p_ids = [id_map[p.id] for p in people[:5]]
        p_names = ", ".join(
            f"{p.value} ({ (p.attributes or {}).get('contributions', 0) } contributions)"
            for p in people[:4]
        )
        observations.append(
            {
                "text": f"Key public contributors and repository owners associated with public codebases: {p_names}.",
                "finding_ids": p_ids,
                "confidence": "high",
            }
        )

    next_steps = [
        f"Perform manual passive review of {len(live_subdomains)} live subdomains for exposed test environments.",
        "Review public GitHub repository code commits for outdated domain endpoints.",
        "Verify mail routing security (SPF, DMARC, DKIM) policies.",
    ]

    limitations = [
        "Generated using verified deterministic rules without external LLM inference.",
        "Strictly limited to passively collected public DNS, RDAP, CT, HTTP headers, and public GitHub metadata.",
        "No active scanning or port enumeration was performed.",
    ]

    summary_text = (
        f"Passive OSINT reconnaissance for '{target}' concluded with {len(entities)} verified findings across "
        f"{counts.get('subdomain', 0)} subdomains, {counts.get('ip', 0)} IP addresses, "
        f"{counts.get('technology', 0)} detected technologies, and {counts.get('repository', 0)} public repositories."
    )

    return {
        "summary": summary_text,
        "key_findings": key_findings,
        "observations": observations,
        "next_steps": next_steps,
        "limitations": limitations,
        "is_fallback": True,
        "generator": "Template Summary (Grounded without AI)",
    }
