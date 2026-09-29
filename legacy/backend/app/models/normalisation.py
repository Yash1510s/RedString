"""Data normalisation utilities per Spec Section 5.4."""

import json
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Return the current time in UTC with timezone awareness."""
    return datetime.now(timezone.utc)


def normalise_hostname(hostname: str) -> str:
    """Normalise hostnames: lowercased, stripped of spaces and trailing dots, punycode encoded.

    Trailing dots are stripped.
    """
    clean = hostname.strip().lower()
    if clean.endswith("."):
        clean = clean[:-1]

    # Handle IDN / Punycode
    try:
        clean = clean.encode("idna").decode("ascii")
    except Exception:
        # Fallback to stripped lowercase if idna conversion fails
        pass

    return clean


def truncate_payload(payload: dict[str, Any], max_bytes: int = 65536) -> dict[str, Any]:
    """Truncate payloads larger than max_bytes (default 64 KB) with a truncated flag."""
    try:
        dumped = json.dumps(payload, default=str)
        if len(dumped.encode("utf-8")) <= max_bytes:
            return payload

        # Payload exceeds limit: truncate representation and mark with flag
        truncated_str = dumped[: max_bytes - 100]
        return {
            "truncated": True,
            "original_length_bytes": len(dumped.encode("utf-8")),
            "partial_data": truncated_str,
        }
    except Exception:
        return {"truncated": True, "error": "Unable to serialize payload"}
