"""Tests for Technology & Cloud Provider Collector."""

from unittest.mock import AsyncMock

import pytest

from app.collectors.tech import TechCollector
from app.core.ssrf_guard import SafeHttpClient


@pytest.mark.asyncio
async def test_tech_collector_detects_headers_and_html():
    mock_http = AsyncMock(spec=SafeHttpClient)
    headers = {
        "server": "cloudflare",
        "cf-ray": "859b12a839f8-IAD",
        "strict-transport-security": "max-age=31536000",
        "content-security-policy": "default-src 'self'",
    }
    body = (
        b"<!DOCTYPE html><html><head><script src='/_next/static/chunks/main.js'>"
        b"</script></head><body><div id='__next'>Hello Next.js</div></body></html>"
    )
    mock_http.get.return_value = (200, headers, body)

    collector = TechCollector(http_client=mock_http)
    result = await collector.collect("example.com")

    assert result.collector == "tech"
    assert result.status == "ok"

    types = [e.type for e in result.entities]
    assert "technology" in types
    assert "cloud_provider" in types

    tech_names = {e.value for e in result.entities if e.type == "technology"}
    assert "Cloudflare" in tech_names
    assert "Next.js" in tech_names
    assert "HSTS" in tech_names
    assert "CSP" in tech_names

    cloud_names = {e.value for e in result.entities if e.type == "cloud_provider"}
    assert "Cloudflare" in cloud_names


@pytest.mark.asyncio
async def test_tech_collector_fallback_to_http():
    mock_http = AsyncMock(spec=SafeHttpClient)
    # First call (HTTPS) raises, second call (HTTP) succeeds
    mock_http.get.side_effect = [
        Exception("TLS handshake failed"),
        (200, {"server": "nginx"}, b"<html>Welcome to Nginx</html>"),
    ]

    collector = TechCollector(http_client=mock_http)
    result = await collector.collect("example.com")

    assert result.collector == "tech"
    assert result.status == "ok"
    tech_names = {e.value for e in result.entities if e.type == "technology"}
    assert "Nginx" in tech_names


@pytest.mark.asyncio
async def test_tech_collector_unreachable():
    mock_http = AsyncMock(spec=SafeHttpClient)
    mock_http.get.side_effect = Exception("Connection refused")

    collector = TechCollector(http_client=mock_http)
    result = await collector.collect("example.com")

    assert result.collector == "tech"
    assert result.status == "partial"
    assert len(result.errors) > 0
