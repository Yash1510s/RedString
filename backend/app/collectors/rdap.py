"""RDAP Domain Intelligence Collector per Spec Section 6 & Safety Rule S6."""

import json
import time
from typing import Any

from app.core.ssrf_guard import SafeHttpClient
from app.models.normalisation import normalise_hostname, utc_now
from app.models.schemas import (
    CollectorError,
    CollectorResult,
    EntityIn,
    EntityType,
    EvidenceIn,
)

COLLECTOR_NAME = "rdap"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 8.0

# Fields to strictly withhold / drop to prevent personal profiling (Rule S6)
PROHIBITED_CONTACT_KEYS = {
    "fn",
    "name",
    "email",
    "tel",
    "voice",
    "adr",
    "street",
    "postal-code",
    "phone",
    "individual",
}


def sanitize_rdap_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize RDAP response: strip all individual registrant personal data (Rule S6)."""
    sanitized: dict[str, Any] = {}

    for key, value in data.items():
        if key.lower() in PROHIBITED_CONTACT_KEYS:
            continue
        if key == "entities" and isinstance(value, list):
            clean_entities = []
            for ent in value:
                clean_ent: dict[str, Any] = {
                    "roles": ent.get("roles", []),
                    "handle": ent.get("handle", "REDACTED"),
                }
                # Check vcardArray
                vcard = ent.get("vcardArray")
                if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list):
                    clean_vcard = []
                    for prop in vcard[1]:
                        if isinstance(prop, list) and len(prop) > 0:
                            prop_name = str(prop[0]).lower()
                            if prop_name in {"version", "kind"}:
                                clean_vcard.append(prop)
                            elif prop_name == "org" and len(prop) > 3:
                                # Legal corporate organization name is allowed
                                clean_vcard.append(prop)
                            else:
                                clean_vcard.append([prop_name, {}, "text", "REDACTED_WITHHELD"])
                    clean_ent["vcardArray"] = [vcard[0], clean_vcard]
                clean_entities.append(clean_ent)
            sanitized["entities"] = clean_entities
        elif isinstance(value, dict):
            sanitized[key] = sanitize_rdap_payload(value)
        else:
            sanitized[key] = value

    return sanitized


class RDAPCollector:
    """Passively retrieves authoritative domain registration data (personal data stripped)."""

    name: str = COLLECTOR_NAME
    version: str = COLLECTOR_VERSION
    timeout_s: int = int(DEFAULT_TIMEOUT)

    def __init__(self, http_client: SafeHttpClient | None = None) -> None:
        self.http_client = http_client or SafeHttpClient(timeout=DEFAULT_TIMEOUT)

    async def collect(self, target: str) -> CollectorResult:
        """Fetch and parse RDAP registration info for the target domain."""
        start_time = time.perf_counter()
        clean_domain = normalise_hostname(target)
        now = utc_now()

        entities: list[EntityIn] = []
        errors: list[CollectorError] = []

        rdap_url = f"https://rdap.org/domain/{clean_domain}"

        try:
            status_code, headers, body = await self.http_client.get(
                rdap_url,
                headers={"Accept": "application/rdap+json, application/json"},
            )

            if status_code == 404:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return CollectorResult(
                    collector=self.name,
                    status="ok",
                    entities=[],
                    relations=[],
                    errors=[
                        CollectorError(
                            code="domain_not_found",
                            message=f"RDAP registry returned 404 for '{clean_domain}'",
                            retryable=False,
                        )
                    ],
                    duration_ms=duration_ms,
                )

            if status_code != 200:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return CollectorResult(
                    collector=self.name,
                    status="partial",
                    entities=[],
                    relations=[],
                    errors=[
                        CollectorError(
                            code="upstream_error",
                            message=f"RDAP query returned HTTP {status_code}",
                            retryable=True,
                        )
                    ],
                    duration_ms=duration_ms,
                )

            data = json.loads(body.decode("utf-8", errors="replace"))
            sanitized = sanitize_rdap_payload(data)

            # Extract registration dates from events
            created_date: str | None = None
            expires_date: str | None = None
            updated_date: str | None = None

            for event in data.get("events", []):
                action = event.get("eventAction", "").lower()
                event_date = event.get("eventDate")
                if action == "registration":
                    created_date = event_date
                elif action == "expiration":
                    expires_date = event_date
                elif action == "last changed":
                    updated_date = event_date

            # Extract registrar name
            registrar_name: str | None = None
            for ent in data.get("entities", []):
                if "registrar" in ent.get("roles", []):
                    # Check vcard org or fn
                    vcard = ent.get("vcardArray", [])
                    if len(vcard) > 1 and isinstance(vcard[1], list):
                        for prop in vcard[1]:
                            if isinstance(prop, list) and len(prop) > 3:
                                if prop[0] in {"fn", "org"}:
                                    registrar_name = str(prop[3])
                                    break
                    if not registrar_name:
                        registrar_name = ent.get("handle")

            # Extract nameservers listed in RDAP
            rdap_nameservers = [
                ns.get("ldhName", "").lower()
                for ns in data.get("nameservers", [])
                if ns.get("ldhName")
            ]

            # Domain attributes
            domain_attrs: dict[str, Any] = {
                "rdap_source": "rdap.org",
                "status_codes": data.get("status", []),
            }
            if registrar_name:
                domain_attrs["registrar"] = registrar_name
            if created_date:
                domain_attrs["registered_at"] = created_date
            if expires_date:
                domain_attrs["expires_at"] = expires_date
            if updated_date:
                domain_attrs["updated_at"] = updated_date
            if rdap_nameservers:
                domain_attrs["rdap_nameservers"] = rdap_nameservers

            ev = EvidenceIn(
                source_name=self.name,
                source_ref=rdap_url,
                raw={
                    "registrar": registrar_name,
                    "dates": {
                        "registered": created_date,
                        "expires": expires_date,
                        "updated": updated_date,
                    },
                    "status": data.get("status", []),
                    "sanitized_rdap": sanitized,
                },
                collected_at=now,
                collector_version=self.version,
            )

            entities.append(
                EntityIn(
                    type=EntityType.domain,
                    value=clean_domain,
                    attributes=domain_attrs,
                    evidence=[ev],
                )
            )

            # If registrar organization identified, record as organization entity
            if registrar_name:
                entities.append(
                    EntityIn(
                        type=EntityType.organization,
                        value=registrar_name,
                        attributes={"role": "domain_registrar"},
                        evidence=[ev],
                    )
                )

        except Exception as exc:
            errors.append(
                CollectorError(
                    code="collector_exception",
                    message=f"RDAP collection failed: {exc}",
                    retryable=True,
                )
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        status = "ok" if entities else "failed"

        return CollectorResult(
            collector=self.name,
            status=status,
            entities=entities,
            relations=[],
            errors=errors,
            duration_ms=duration_ms,
        )
