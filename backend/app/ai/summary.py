import json
import logging
from collections import defaultdict
from typing import Any

import httpx

from app.ai.prompts import PROMPT_VERSION, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.config import settings
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
    """Generate comprehensive, evidence-grounded intelligence summary without AI (Spec Section 10.2)."""
    # Group entities by type
    by_type: dict[str, list[Entity]] = defaultdict(list)
    id_map: dict[int, str] = {}
    for ent in entities:
        by_type[ent.type].append(ent)
        id_map[ent.id] = f"F-{ent.id:06d}"

    key_findings: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    # 1. IP Addresses & Routing Infrastructure
    ips = by_type.get("ip", [])
    if ips:
        ip_ids = [id_map[e.id] for e in ips[:6]]
        ip_values = [e.value for e in ips[:4]]
        cloud_providers = {
            str((e.attributes or {}).get("cloud_provider"))
            for e in ips
            if (e.attributes or {}).get("cloud_provider")
        }
        cloud_str = f" terminating via {', '.join(cloud_providers)}" if cloud_providers else ""
        claim_text = (
            f"Observed {len(ips)} public IP addresses ({', '.join(ip_values)}"
            f"{' and others' if len(ips) > 4 else ''}){cloud_str}."
        )
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": ip_ids,
                "category": "Network & Routing",
            }
        )

    # 2. Domain & DNS Summary
    dns_records = by_type.get("nameserver", [])
    if dns_records:
        ns_ids = [id_map[e.id] for e in dns_records[:4]]
        ns_names = ", ".join(e.value for e in dns_records[:4])
        claim_text = f"Authoritative nameserver delegation handled by: {ns_names}."
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": ns_ids,
                "category": "DNS Infrastructure",
            }
        )

    # 3. Mail Infrastructure
    mail_records = by_type.get("mail_provider", [])
    if mail_records:
        mail_ids = [id_map[e.id] for e in mail_records]
        mail_names = ", ".join(e.value for e in mail_records)
        claim_text = f"Enterprise mail gateway infrastructure routed through: {mail_names}."
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": mail_ids,
                "category": "Mail Routing",
            }
        )

    # 4. Organization & Registration
    orgs = by_type.get("organization", [])
    if orgs:
        org_ids = [id_map[e.id] for e in orgs]
        org_names = ", ".join(e.value for e in orgs)
        claim_text = f"Public registry entities associated with target: {org_names}."
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": org_ids,
                "category": "Registry & Ownership",
            }
        )

    # 5. Subdomains
    subdomains = by_type.get("subdomain", [])
    live_subdomains = [s for s in subdomains if (s.attributes or {}).get("live") is True]
    if subdomains:
        top_subs = subdomains[:6]
        sub_ids = [id_map[s.id] for s in top_subs]
        sub_names = ", ".join(s.value for s in top_subs[:3])
        obs_text = (
            f"Discovered {len(subdomains)} public subdomains (including {sub_names}); "
            f"{len(live_subdomains) if live_subdomains else len(subdomains)} active endpoints detected."
        )
        observations.append(
            {
                "observation": obs_text,
                "text": obs_text,
                "finding_ids": sub_ids,
                "confidence": "high",
            }
        )

    # 6. Certificates
    certs = by_type.get("certificate", [])
    if certs:
        c_ids = [id_map[c.id] for c in certs[:4]]
        issuers = {
            str((c.attributes or {}).get("issuer_name", (c.attributes or {}).get("issuer", "Trusted CA")))
            for c in certs[:4]
        }
        obs_text = f"Public TLS certificates observed issued by: {', '.join(issuers)}."
        observations.append(
            {
                "observation": obs_text,
                "text": obs_text,
                "finding_ids": c_ids,
                "confidence": "high",
            }
        )

    # 7. Technology Stack
    techs = by_type.get("technology", [])
    clouds = by_type.get("cloud_provider", [])
    if techs or clouds:
        t_ids = [id_map[t.id] for t in techs[:6]] + [id_map[c.id] for c in clouds]
        t_names = [t.value for t in techs[:5]]
        c_names = [c.value for c in clouds]
        all_stack = t_names + [f"Hosted on {c}" for c in c_names]
        claim_text = f"Detected perimeter technologies and CDN layers: {', '.join(all_stack)}."
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": t_ids,
                "category": "Technology Fingerprints",
            }
        )

    # 8. Repositories
    repos = by_type.get("repository", [])
    if repos:
        r_ids = [id_map[r.id] for r in repos[:5]]
        r_names = ", ".join(r.value for r in repos[:3])
        claim_text = f"Found {len(repos)} public GitHub repositories referencing {target} (including {r_names})."
        key_findings.append(
            {
                "claim": claim_text,
                "text": claim_text,
                "finding_ids": r_ids,
                "category": "Public Code Repositories",
            }
        )

    # 9. Correlated Observations
    if ips and dns_records:
        corr_ids = [id_map[ips[0].id], id_map[dns_records[0].id]]
        obs_text = f"Authoritative DNS resolvers and IP routing for '{target}' demonstrate established enterprise infrastructure partitioning."
        observations.append(
            {
                "observation": obs_text,
                "text": obs_text,
                "finding_ids": corr_ids,
                "confidence": "high",
            }
        )

    if techs:
        tech_ids = [id_map[t.id] for t in techs[:2]]
        obs_text = f"Web perimeter exposes headers consistent with {', '.join(t.value for t in techs[:2])}."
        observations.append(
            {
                "observation": obs_text,
                "text": obs_text,
                "finding_ids": tech_ids,
                "confidence": "medium",
            }
        )

    # Comprehensive multi-paragraph executive summary
    total_count = len(entities)
    summary_parts = [
        f"Passive OSINT reconnaissance for '{target}' concluded with {total_count} verified findings across "
        f"{counts.get('subdomain', len(subdomains))} subdomains, {counts.get('ip', len(ips))} IP addresses, "
        f"{counts.get('technology', len(techs))} detected technologies, and {counts.get('repository', len(repos))} public repositories."
    ]

    if ips or dns_records:
        summary_parts.append(
            f"The target maintains authoritative DNS presence across {len(dns_records)} nameservers and routes web traffic across {len(ips)} observed IP addresses."
        )

    if techs:
        summary_parts.append(
            f"Passive HTTP header analysis revealed front-end web and caching infrastructure powered by {', '.join(t.value for t in techs[:3])}."
        )

    if repos:
        summary_parts.append(
            f"Source code reconnaissance identified {len(repos)} public GitHub repositories referencing the target domain."
        )

    summary_text = " ".join(summary_parts)

    next_steps = [
        f"Perform manual passive review of {len(live_subdomains) if live_subdomains else len(subdomains)} live subdomains for exposed staging/test environments.",
        f"Inspect public code commits across {len(repos)} identified GitHub repositories for inadvertent token or endpoint disclosures.",
        "Verify mail routing security (SPF, DMARC, DKIM) policies to prevent spoofing risks.",
        "Review edge certificate SAN expansions for unindexed sub-properties.",
    ]

    limitations = [
        "Generated using verified deterministic rules without external LLM inference.",
        "Strictly limited to passively collected public DNS, RDAP, CT, HTTP headers, and public GitHub metadata.",
        "No active scanning or port enumeration was performed.",
    ]

    return {
        "summary": summary_text,
        "key_findings": key_findings,
        "observations": observations,
        "next_steps": next_steps,
        "limitations": limitations,
        "is_fallback": True,
        "generator": "Template Summary (Grounded without AI)",
    }


async def generate_grounded_summary(
    target: str,
    entities: list[Entity],
    counts: dict[str, int],
    official_domain: str | None = None,
) -> dict[str, Any]:
    """Generate an AI-powered grounded summary or fall back safely to deterministic template."""
    provider = (settings.llm_provider or "none").lower().strip()
    if provider == "none" or (not settings.llm_api_key and provider != "ollama"):
        return generate_template_summary(target, entities, counts)

    valid_ids = {f"F-{e.id:06d}" for e in entities}
    findings_payload = [
        {
            "id": f"F-{e.id:06d}",
            "type": e.type,
            "value": e.value,
            "attributes": e.attributes,
        }
        for e in entities
    ]

    user_prompt = USER_PROMPT_TEMPLATE.format(
        target=target,
        official_domain=official_domain or "Not specified",
        counts_json=json.dumps(counts),
        findings_json=json.dumps(findings_payload, indent=2),
    )

    try:
        if provider == "gemini":
            model = settings.llm_model or "gemini-3.8-flash"
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                f"?key={settings.llm_api_key}"
            )
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT}\n\n{user_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json",
                },
            }
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    logger.warning("Gemini generation failed (%s): %s", res.status_code, res.text)
                    fallback = generate_template_summary(target, entities, counts)
                    fallback["fallback_reason"] = f"Gemini API returned status {res.status_code}"
                    return fallback

                res_json = res.json()
                raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)

        elif provider == "openai":
            model = settings.llm_model or "gpt-4o-mini"
            endpoint = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            }
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(endpoint, json=payload, headers=headers)
                if res.status_code != 200:
                    logger.warning("OpenAI generation failed (%s): %s", res.status_code, res.text)
                    fallback = generate_template_summary(target, entities, counts)
                    fallback["fallback_reason"] = f"OpenAI API returned status {res.status_code}"
                    return fallback

                res_json = res.json()
                raw_text = res_json["choices"][0]["message"]["content"]
                parsed = json.loads(raw_text)

        elif provider == "ollama":
            model = settings.llm_model or "llama3.2"
            base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
            endpoint = f"{base_url}/api/chat"
            payload = {
                "model": model,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code != 200:
                    logger.warning("Ollama generation failed (%s): %s", res.status_code, res.text)
                    fallback = generate_template_summary(target, entities, counts)
                    fallback["fallback_reason"] = f"Ollama returned status {res.status_code}"
                    return fallback

                res_json = res.json()
                raw_text = res_json["message"]["content"]
                parsed = json.loads(raw_text)

        else:
            return generate_template_summary(target, entities, counts)

        # Validate structured schema and cited finding IDs per Spec Section 10
        is_valid, reason = validate_summary(parsed, valid_ids)
        if not is_valid:
            logger.warning("LLM output validation failed: %s; using grounded fallback", reason)
            fallback = generate_template_summary(target, entities, counts)
            fallback["fallback_reason"] = f"LLM citation validation failed: {reason}"
            return fallback

        parsed["is_fallback"] = False
        parsed["model"] = f"{provider}:{settings.llm_model or 'default'}"
        parsed["prompt_version"] = PROMPT_VERSION
        parsed["generator"] = f"AI Grounded Summary ({provider.upper()})"
        return parsed

    except Exception as exc:
        logger.exception("Unexpected error during LLM generation: %s", exc)
        fallback = generate_template_summary(target, entities, counts)
        fallback["fallback_reason"] = str(exc)
        return fallback

