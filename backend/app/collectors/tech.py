"""Technology Stack and Cloud Provider Collector per Spec Section 6."""

import ipaddress
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from app.core.ssrf_guard import SafeHttpClient
from app.models.normalisation import normalise_hostname, utc_now
from app.models.schemas import (
    CollectorError,
    CollectorResult,
    Confidence,
    EntityIn,
    EntityType,
    EvidenceIn,
    RelationIn,
    RelationType,
)

logger = logging.getLogger(__name__)

COLLECTOR_NAME = "tech"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 10.0
MAX_HTML_BODY_BYTES = 512 * 1024  # 512 KB limit per Spec 6
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def load_fingerprints() -> list[dict[str, Any]]:
    """Load technology fingerprint rules from data/fingerprints/technologies.json."""
    data_path = PROJECT_ROOT / "data" / "fingerprints" / "technologies.json"
    if not data_path.exists():
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            rules = content.get("rules", [])
            return [dict(r) for r in rules if isinstance(r, dict)]
    except Exception as exc:
        logger.error("Failed to load technology fingerprints: %s", exc)
        return []


def load_cloud_ranges() -> list[dict[str, Any]]:
    """Load cloud provider CIDR ranges from data/cloud_ranges/ranges.json."""
    data_path = PROJECT_ROOT / "data" / "cloud_ranges" / "ranges.json"
    if not data_path.exists():
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            providers = content.get("providers", [])
            return [dict(p) for p in providers if isinstance(p, dict)]
    except Exception as exc:
        logger.error("Failed to load cloud ranges: %s", exc)
        return []


class TechCollector:
    """Passively detects web servers, frontend frameworks, security headers, and cloud hosts."""

    name: str = COLLECTOR_NAME
    version: str = COLLECTOR_VERSION
    timeout_s: int = int(DEFAULT_TIMEOUT)

    def __init__(self, http_client: SafeHttpClient | None = None) -> None:
        self.http_client = http_client or SafeHttpClient(timeout=DEFAULT_TIMEOUT)
        self.fingerprints = load_fingerprints()
        self.cloud_providers = load_cloud_ranges()

    def _match_cloud_provider(self, ip_str: str) -> str | None:
        """Check if an IP falls within known cloud/CDN provider CIDRs."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return None

        for prov in self.cloud_providers:
            prov_name = prov.get("name")
            for cidr in prov.get("cidrs", []):
                try:
                    if ip_obj in ipaddress.ip_network(cidr, strict=False):
                        return prov_name
                except ValueError:
                    continue
        return None

    async def collect(self, target: str) -> CollectorResult:
        """Fetch target homepage via SSRF guard, match fingerprints, and check cloud hosting."""
        start_time = time.perf_counter()
        clean_domain = normalise_hostname(target)
        now = utc_now()

        entities: list[EntityIn] = []
        relations: list[RelationIn] = []
        errors: list[CollectorError] = []

        headers: dict[str, str] = {}
        body_bytes = b""
        final_url = f"https://{clean_domain}/"
        status_code = 0

        # Try HTTPS first
        try:
            status_code, headers, body_bytes = await self.http_client.get(
                final_url,
                headers={"User-Agent": "RedString-OSINT-Passive-Scanner/1.0"},
            )
        except Exception as https_err:
            logger.info(
                "HTTPS GET failed for %s (%s), attempting HTTP fallback",
                clean_domain,
                https_err,
            )
            final_url = f"http://{clean_domain}/"
            try:
                status_code, headers, body_bytes = await self.http_client.get(
                    final_url,
                    headers={"User-Agent": "RedString-OSINT-Passive-Scanner/1.0"},
                )
            except Exception as http_err:
                logger.warning("HTTP fallback failed for %s: %s", clean_domain, http_err)
                errors.append(
                    CollectorError(
                        code="http_get_failed",
                        message=f"Target homepage unreachable: {http_err}",
                        retryable=True,
                    )
                )

        if not headers and not body_bytes:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                collector=self.name,
                status="partial" if errors else "ok",
                entities=[],
                relations=[],
                errors=errors,
                duration_ms=duration_ms,
            )

        # Normalize header keys to lowercase
        norm_headers = {k.lower(): str(v) for k, v in headers.items()}
        # Truncate body for analysis
        html_sample = body_bytes[:MAX_HTML_BODY_BYTES].decode("utf-8", errors="replace")

        # Match technology fingerprints
        seen_tech: set[str] = set()
        for rule in self.fingerprints:
            tech_name = rule.get("name")
            if not tech_name or tech_name in seen_tech:
                continue

            matched = False
            evidence_detail: dict[str, Any] = {"rule_name": tech_name}

            # Check header patterns
            for h_key, h_pattern in rule.get("headers", {}).items():
                if h_key in norm_headers:
                    h_val = norm_headers[h_key]
                    if re.search(h_pattern, h_val):
                        matched = True
                        evidence_detail["matched_header"] = {h_key: h_val}
                        break

            # Check HTML patterns
            if not matched and "html" in rule:
                for pattern in rule["html"]:
                    if pattern in html_sample:
                        matched = True
                        evidence_detail["matched_html_pattern"] = pattern
                        break

            if matched:
                seen_tech.add(tech_name)
                conf_str = rule.get("confidence", "medium")
                conf = (
                    Confidence.high
                    if conf_str == "high"
                    else (Confidence.medium if conf_str == "medium" else Confidence.low)
                )

                ev_tech = EvidenceIn(
                    source_name=self.name,
                    source_ref=final_url,
                    raw={
                        "technology": tech_name,
                        "category": rule.get("category", "General"),
                        "status_code": status_code,
                        "matched_rule": evidence_detail,
                    },
                    collected_at=now,
                    collector_version=self.version,
                )

                entities.append(
                    EntityIn(
                        type=EntityType.technology,
                        value=tech_name,
                        attributes={
                            "category": rule.get("category", "General"),
                            "confidence": conf_str,
                        },
                        evidence=[ev_tech],
                    )
                )

                relations.append(
                    RelationIn(
                        source=(EntityType.domain, clean_domain),
                        target=(EntityType.technology, tech_name),
                        type=RelationType.USES_TECH,
                        confidence=conf,
                        evidence=[ev_tech],
                    )
                )

        # Check cloud/CDN provider via headers (e.g., cf-ray, server, x-amz-cf-id)
        cloud_name: str | None = None
        if "cf-ray" in norm_headers or "cloudflare" in norm_headers.get("server", "").lower():
            cloud_name = "Cloudflare"
        elif "x-amz-cf-id" in norm_headers or "cloudfront" in norm_headers.get("via", "").lower():
            cloud_name = "AWS"
        elif "x-fastly-request-id" in norm_headers:
            cloud_name = "Fastly"

        if cloud_name:
            ev_cloud = EvidenceIn(
                source_name=self.name,
                source_ref=final_url,
                raw={"provider": cloud_name, "headers": norm_headers},
                collected_at=now,
                collector_version=self.version,
            )
            entities.append(
                EntityIn(
                    type=EntityType.cloud_provider,
                    value=cloud_name,
                    attributes={"detected_via": "http_headers"},
                    evidence=[ev_cloud],
                )
            )
            relations.append(
                RelationIn(
                    source=(EntityType.domain, clean_domain),
                    target=(EntityType.cloud_provider, cloud_name),
                    type=RelationType.HOSTED_ON,
                    confidence=Confidence.high,
                    evidence=[ev_cloud],
                )
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return CollectorResult(
            collector=self.name,
            status="ok" if entities else ("partial" if errors else "ok"),
            entities=entities,
            relations=relations,
            errors=errors,
            duration_ms=duration_ms,
        )
