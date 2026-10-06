"""System information and integration status endpoint per UI_SPEC.md §5.4."""

from typing import Any

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("", summary="Get integration and system status")
async def get_system_status() -> dict[str, Any]:
    """Return read-only diagnostic info without exposing secret values."""
    has_github_token = bool(settings.github_token and len(settings.github_token.strip()) > 0)
    has_llm_key = bool(settings.llm_api_key and len(settings.llm_api_key.strip()) > 0)

    llm_status = "Deterministic Grounded Template (Offline)"
    if settings.llm_provider and settings.llm_provider != "none":
        llm_status = f"{settings.llm_provider.capitalize()} ({'Key Configured' if has_llm_key else 'Local/No Key'})"

    return {
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "SQLite (Async SQLAlchemy 2.0)",
        "ssrf_guard": "Enforced (Blocking loopback, LAN, Link-local, Cloud metadata)",
        "cache_ttl_hours": settings.cache_ttl_seconds // 3600,
        "integrations": [
            {
                "name": "GitHub Public API",
                "status": "Configured" if has_github_token else "Unconfigured (Rate-limited to 60 req/hr)",
                "note": "Add GITHUB_TOKEN to raise public API limit to 5,000 req/hr.",
            },
            {
                "name": "LLM Summary Engine",
                "status": llm_status,
                "note": "Falls back to 100% deterministic grounded template if no key is present.",
            },
            {
                "name": "Certificate Transparency (crt.sh & Certspotter)",
                "status": "Active (Public CT logs with fallback)",
                "note": "Passive discovery of registered SSL/TLS subdomains.",
            },
            {
                "name": "DNS Resolvers",
                "status": "Active (Authoritative system resolution)",
                "note": "Passive resolution of A, AAAA, MX, TXT, NS, SOA, SPF, and DMARC.",
            },
            {
                "name": "Cloud IP Ranges",
                "status": "Bundled (AWS & Cloudflare published CIDRs)",
                "note": "Dated static JSON range matchers.",
            },
        ],
    }
