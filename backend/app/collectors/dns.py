"""DNS Passive Intelligence Collector per Spec Section 6."""

import time
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

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

COLLECTOR_NAME = "dns"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 5.0

# Known MX host patterns to identify mail providers
KNOWN_MAIL_PROVIDERS = [
    ("google", "Google Workspace", ["google.com", "googlemail.com", "aspmx.l.google.com"]),
    ("microsoft", "Microsoft 365", ["outlook.com", "protection.outlook.com", "microsoft.com"]),
    ("proton", "ProtonMail", ["protonmail.ch", "proton.me"]),
    ("fastmail", "Fastmail", ["messagingengine.com"]),
    ("zoho", "Zoho Mail", ["zoho.com", "zoho.eu"]),
    ("cloudflare", "Cloudflare Email Routing", ["mx.cloudflare.net"]),
    ("mimecast", "Mimecast", ["mimecast.com"]),
    ("proofpoint", "Proofpoint", ["pphosted.com"]),
    ("amazon", "Amazon SES", ["amazonses.com"]),
]


def detect_mail_provider(mx_hostname: str) -> tuple[str, str] | None:
    """Detect known enterprise or consumer mail providers from MX hostnames."""
    clean_mx = mx_hostname.lower()
    for provider_key, provider_name, domains in KNOWN_MAIL_PROVIDERS:
        if any(d in clean_mx for d in domains):
            return provider_key, provider_name
    return None


class DNSCollector:
    """Passively collects DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA), SPF, and DMARC."""

    name: str = COLLECTOR_NAME
    version: str = COLLECTOR_VERSION
    timeout_s: int = int(DEFAULT_TIMEOUT)

    def __init__(self, resolver: dns.asyncresolver.Resolver | None = None) -> None:
        if resolver is None:
            self.resolver = dns.asyncresolver.Resolver()
            self.resolver.lifetime = DEFAULT_TIMEOUT
        else:
            self.resolver = resolver

    async def _query_record(
        self,
        domain: str,
        rtype: str,
    ) -> list[str]:
        """Query a single DNS record type, returning string answers or empty list."""
        try:
            answer = await self.resolver.resolve(domain, rtype)
            results: list[str] = []
            for rdata in answer:
                text = rdata.to_text().strip('"')
                results.append(text)
            return results
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        except dns.exception.Timeout:
            return []
        except Exception:
            return []

    async def collect(self, target: str) -> CollectorResult:
        """Run complete passive DNS collection for root domain and www."""
        start_time = time.perf_counter()
        clean_domain = normalise_hostname(target)
        now = utc_now()

        entities: list[EntityIn] = []
        relations: list[RelationIn] = []
        errors: list[CollectorError] = []

        # We query the apex domain and www
        query_targets = [clean_domain]
        if not clean_domain.startswith("www."):
            query_targets.append(f"www.{clean_domain}")

        # Track observed mail providers to avoid duplicate entities within collector
        detected_providers: set[str] = set()

        for q_domain in query_targets:
            # 1. A Records (IPv4)
            a_records = await self._query_record(q_domain, "A")
            if a_records:
                ev_a = EvidenceIn(
                    source_name=self.name,
                    source_ref=f"A {q_domain}",
                    raw={"answers": a_records, "rtype": "A", "query": q_domain},
                    collected_at=now,
                    collector_version=self.version,
                )
                for ip_str in a_records:
                    entities.append(
                        EntityIn(
                            type=EntityType.ip,
                            value=ip_str,
                            attributes={"family": "ipv4", "record_type": "A"},
                            evidence=[ev_a],
                        )
                    )
                    relations.append(
                        RelationIn(
                            source=(EntityType.domain, q_domain),
                            target=(EntityType.ip, ip_str),
                            type=RelationType.RESOLVES_TO,
                            confidence=Confidence.high,
                            evidence=[ev_a],
                        )
                    )

            # 2. AAAA Records (IPv6)
            aaaa_records = await self._query_record(q_domain, "AAAA")
            if aaaa_records:
                ev_aaaa = EvidenceIn(
                    source_name=self.name,
                    source_ref=f"AAAA {q_domain}",
                    raw={"answers": aaaa_records, "rtype": "AAAA", "query": q_domain},
                    collected_at=now,
                    collector_version=self.version,
                )
                for ip_str in aaaa_records:
                    entities.append(
                        EntityIn(
                            type=EntityType.ip,
                            value=ip_str,
                            attributes={"family": "ipv6", "record_type": "AAAA"},
                            evidence=[ev_aaaa],
                        )
                    )
                    relations.append(
                        RelationIn(
                            source=(EntityType.domain, q_domain),
                            target=(EntityType.ip, ip_str),
                            type=RelationType.RESOLVES_TO,
                            confidence=Confidence.high,
                            evidence=[ev_aaaa],
                        )
                    )

            # 3. CNAME Records
            cname_records = await self._query_record(q_domain, "CNAME")
            if cname_records:
                ev_cname = EvidenceIn(
                    source_name=self.name,
                    source_ref=f"CNAME {q_domain}",
                    raw={"answers": cname_records, "rtype": "CNAME", "query": q_domain},
                    collected_at=now,
                    collector_version=self.version,
                )
                for cname_target in cname_records:
                    clean_cname = normalise_hostname(cname_target)
                    entities.append(
                        EntityIn(
                            type=EntityType.domain,
                            value=clean_cname,
                            attributes={"is_cname_target": True},
                            evidence=[ev_cname],
                        )
                    )
                    relations.append(
                        RelationIn(
                            source=(EntityType.domain, q_domain),
                            target=(EntityType.domain, clean_cname),
                            type=RelationType.RESOLVES_TO,
                            confidence=Confidence.high,
                            evidence=[ev_cname],
                        )
                    )

        # 4. NS Records (Nameservers) - apex domain only
        ns_records = await self._query_record(clean_domain, "NS")
        if ns_records:
            ev_ns = EvidenceIn(
                source_name=self.name,
                source_ref=f"NS {clean_domain}",
                raw={"answers": ns_records, "rtype": "NS", "query": clean_domain},
                collected_at=now,
                collector_version=self.version,
            )
            for ns_host in ns_records:
                clean_ns = normalise_hostname(ns_host)
                entities.append(
                    EntityIn(
                        type=EntityType.nameserver,
                        value=clean_ns,
                        attributes={"role": "authoritative_nameserver"},
                        evidence=[ev_ns],
                    )
                )
                relations.append(
                    RelationIn(
                        source=(EntityType.domain, clean_domain),
                        target=(EntityType.nameserver, clean_ns),
                        type=RelationType.USES_NS,
                        confidence=Confidence.high,
                        evidence=[ev_ns],
                    )
                )

        # 5. MX Records (Mail Exchangers)
        mx_records = await self._query_record(clean_domain, "MX")
        if mx_records:
            ev_mx = EvidenceIn(
                source_name=self.name,
                source_ref=f"MX {clean_domain}",
                raw={"answers": mx_records, "rtype": "MX", "query": clean_domain},
                collected_at=now,
                collector_version=self.version,
            )
            for mx_entry in mx_records:
                # mx_entry typically is "10 aspmx.l.google.com."
                parts = mx_entry.split()
                priority = parts[0] if len(parts) > 1 else "0"
                mx_host = parts[1] if len(parts) > 1 else parts[0]
                clean_mx_host = normalise_hostname(mx_host)

                # Identify provider
                detected = detect_mail_provider(clean_mx_host)
                if detected:
                    provider_key, provider_name = detected
                    if provider_key not in detected_providers:
                        detected_providers.add(provider_key)
                        entities.append(
                            EntityIn(
                                type=EntityType.mail_provider,
                                value=provider_name,
                                attributes={"provider_key": provider_key, "priority": priority},
                                evidence=[ev_mx],
                            )
                        )
                        relations.append(
                            RelationIn(
                                source=(EntityType.domain, clean_domain),
                                target=(EntityType.mail_provider, provider_name),
                                type=RelationType.USES_MAIL,
                                confidence=Confidence.high,
                                evidence=[ev_mx],
                            )
                        )

        # 6. TXT Records: SPF & DMARC Detection
        txt_records = await self._query_record(clean_domain, "TXT")
        spf_record: str | None = None
        for txt in txt_records:
            if "v=spf1" in txt:
                spf_record = txt
                break

        # DMARC query on _dmarc.domain
        dmarc_records = await self._query_record(f"_dmarc.{clean_domain}", "TXT")
        dmarc_record: str | None = None
        for txt in dmarc_records:
            if "v=DMARC1" in txt:
                dmarc_record = txt
                break

        # Attach domain email security attributes
        domain_attrs: dict[str, Any] = {}
        if spf_record:
            domain_attrs["spf_record"] = spf_record
        if dmarc_record:
            domain_attrs["dmarc_record"] = dmarc_record

        if domain_attrs:
            ev_sec = EvidenceIn(
                source_name=self.name,
                source_ref=f"TXT {clean_domain}",
                raw={
                    "spf": spf_record,
                    "dmarc": dmarc_record,
                    "all_txt": txt_records,
                },
                collected_at=now,
                collector_version=self.version,
            )
            entities.append(
                EntityIn(
                    type=EntityType.domain,
                    value=clean_domain,
                    attributes=domain_attrs,
                    evidence=[ev_sec],
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
