"""Certificate Transparency (CT) Collector per Spec Section 6."""

import asyncio
import json
import logging
import time
from typing import Any

import dns.asyncresolver
import dns.resolver

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

COLLECTOR_NAME = "ct"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 12.0
MAX_SUBDOMAINS_TO_RESOLVE = 40


class CTCollector:
    """Passively discovers certificates, SANs, and subdomains via Certificate Transparency logs."""

    name: str = COLLECTOR_NAME
    version: str = COLLECTOR_VERSION
    timeout_s: int = int(DEFAULT_TIMEOUT)

    def __init__(
        self,
        http_client: SafeHttpClient | None = None,
        resolver: dns.asyncresolver.Resolver | None = None,
    ) -> None:
        self.http_client = http_client or SafeHttpClient(timeout=DEFAULT_TIMEOUT)
        if resolver is None:
            self.resolver = dns.asyncresolver.Resolver()
            self.resolver.lifetime = 3.0
        else:
            self.resolver = resolver

    async def _resolve_ip(self, hostname: str) -> list[str]:
        """Check if a discovered subdomain resolves to live IPs."""
        try:
            answer = await self.resolver.resolve(hostname, "A")
            return [rdata.to_text().strip('"') for rdata in answer]
        except Exception:
            return []

    async def collect(self, target: str) -> CollectorResult:
        """Query Certificate Transparency logs on crt.sh, extract subdomains, and check liveness."""
        start_time = time.perf_counter()
        clean_domain = normalise_hostname(target)
        now = utc_now()

        entities: list[EntityIn] = []
        relations: list[RelationIn] = []
        errors: list[CollectorError] = []

        crt_url = f"https://crt.sh/?q=%.{clean_domain}&output=json"

        cert_entries: list[dict[str, Any]] = []
        try:
            status_code, headers, body = await self.http_client.get(
                crt_url,
                headers={"Accept": "application/json"},
            )

            if status_code == 200:
                raw_text = body.decode("utf-8", errors="replace").strip()
                if raw_text:
                    cert_entries = json.loads(raw_text)
            else:
                errors.append(
                    CollectorError(
                        code="crtsh_status_error",
                        message=f"crt.sh returned HTTP {status_code}",
                        retryable=True,
                    )
                )
        except Exception as exc:
            logger.warning("crt.sh primary query failed: %s", exc)
            errors.append(
                CollectorError(
                    code="crtsh_timeout_or_error",
                    message=f"Certificate Transparency service unavailable: {exc}",
                    retryable=True,
                )
            )

        if not cert_entries:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                collector=self.name,
                status="partial" if errors else "ok",
                entities=[],
                relations=[],
                errors=errors,
                duration_ms=duration_ms,
            )

        # Track observed subdomains and certificates
        observed_subdomains: set[str] = set()
        seen_cert_serials: set[str] = set()

        for entry in cert_entries[:50]:  # Cap processed certificate entries
            serial_number = str(entry.get("serial_number", entry.get("id", "")))
            issuer_name = entry.get("issuer_name", "Unknown Issuer")
            not_before = entry.get("not_before")
            not_after = entry.get("not_after")
            name_value = entry.get("name_value", "")

            # Split name_value which can contain multiple SANs separated by newlines
            raw_names = name_value.split("\n")
            san_list: list[str] = []
            has_wildcard = False

            for raw_name in raw_names:
                n = raw_name.strip().lower()
                if not n:
                    continue
                if n.startswith("*."):
                    has_wildcard = True
                    n = n[2:]  # Strip wildcard prefix for subdomain tracking

                # Check if it is a subdomain of our target
                if n.endswith(f".{clean_domain}") or n == clean_domain:
                    san_list.append(n)
                    if n != clean_domain:
                        observed_subdomains.add(n)

            # Record certificate entity
            if serial_number and serial_number not in seen_cert_serials:
                seen_cert_serials.add(serial_number)
                cert_val = f"cert-{serial_number[:16]}"
                ev_cert = EvidenceIn(
                    source_name=self.name,
                    source_ref=crt_url,
                    raw={
                        "serial_number": serial_number,
                        "issuer_name": issuer_name,
                        "not_before": not_before,
                        "not_after": not_after,
                        "sans": san_list,
                        "wildcard": has_wildcard,
                    },
                    collected_at=now,
                    collector_version=self.version,
                )

                entities.append(
                    EntityIn(
                        type=EntityType.certificate,
                        value=cert_val,
                        attributes={
                            "serial_number": serial_number,
                            "issuer_name": issuer_name,
                            "not_before": not_before,
                            "not_after": not_after,
                            "wildcard": has_wildcard,
                            "san_count": len(san_list),
                        },
                        evidence=[ev_cert],
                    )
                )

                # COVERS relation to root domain
                relations.append(
                    RelationIn(
                        source=(EntityType.certificate, cert_val),
                        target=(EntityType.domain, clean_domain),
                        type=RelationType.COVERS,
                        confidence=Confidence.high,
                        evidence=[ev_cert],
                    )
                )

        # Batch resolve up to MAX_SUBDOMAINS_TO_RESOLVE subdomains
        subdomains_to_check = list(observed_subdomains)[:MAX_SUBDOMAINS_TO_RESOLVE]
        resolve_tasks = [self._resolve_ip(sub) for sub in subdomains_to_check]
        dns_results = await asyncio.gather(*resolve_tasks, return_exceptions=True)

        for sub, ips_or_err in zip(subdomains_to_check, dns_results, strict=False):
            resolved_ips = ips_or_err if isinstance(ips_or_err, list) else []
            is_live = len(resolved_ips) > 0
            conf = Confidence.high if is_live else Confidence.medium

            ev_sub = EvidenceIn(
                source_name=self.name,
                source_ref=f"crt.sh SAN for {clean_domain}",
                raw={
                    "subdomain": sub,
                    "live": is_live,
                    "resolved_ips": resolved_ips,
                },
                collected_at=now,
                collector_version=self.version,
            )

            entities.append(
                EntityIn(
                    type=EntityType.subdomain,
                    value=sub,
                    attributes={"live": is_live, "resolved_ips": resolved_ips},
                    evidence=[ev_sub],
                )
            )

            # HAS_SUBDOMAIN relation
            relations.append(
                RelationIn(
                    source=(EntityType.domain, clean_domain),
                    target=(EntityType.subdomain, sub),
                    type=RelationType.HAS_SUBDOMAIN,
                    confidence=conf,
                    evidence=[ev_sub],
                )
            )

            # If resolved to live IPs, create IP entity & RESOLVES_TO
            for ip_val in resolved_ips:
                entities.append(
                    EntityIn(
                        type=EntityType.ip,
                        value=ip_val,
                        attributes={"family": "ipv4", "discovered_via": "ct_subdomain"},
                        evidence=[ev_sub],
                    )
                )
                relations.append(
                    RelationIn(
                        source=(EntityType.subdomain, sub),
                        target=(EntityType.ip, ip_val),
                        type=RelationType.RESOLVES_TO,
                        confidence=Confidence.high,
                        evidence=[ev_sub],
                    )
                )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        status = "ok" if (entities or relations) else "partial"

        return CollectorResult(
            collector=self.name,
            status=status,
            entities=entities,
            relations=relations,
            errors=errors,
            duration_ms=duration_ms,
        )
