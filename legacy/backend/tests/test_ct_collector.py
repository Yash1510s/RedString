"""Tests for Certificate Transparency (CT) Collector."""

import json
from unittest.mock import AsyncMock

import pytest

from app.collectors.ct import CTCollector
from app.core.ssrf_guard import SafeHttpClient


@pytest.fixture
def mock_resolver():
    resolver = AsyncMock()
    # Mock resolve to return an IP for some subdomains and fail for others
    class FakeRdata:
        def __init__(self, ip):
            self._ip = ip

        def to_text(self):
            return self._ip

    async def fake_resolve(hostname, qtype):
        if "api" in hostname:
            return [FakeRdata("93.184.216.34")]
        raise Exception("NXDOMAIN")

    resolver.resolve = AsyncMock(side_effect=fake_resolve)
    return resolver


@pytest.mark.asyncio
async def test_ct_collector_success(mock_resolver):
    mock_http = AsyncMock(spec=SafeHttpClient)
    raw_payload = [
        {
            "id": 1234567,
            "serial_number": "04a1b2c3d4e5f6",
            "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
            "not_before": "2026-01-01T00:00:00",
            "not_after": "2026-04-01T00:00:00",
            "name_value": "example.com\napi.example.com\n*.example.com\nmail.example.com",
        }
    ]
    mock_http.get.return_value = (200, {}, json.dumps(raw_payload).encode("utf-8"))

    collector = CTCollector(http_client=mock_http, resolver=mock_resolver)
    result = await collector.collect("example.com")

    assert result.collector == "ct"
    assert result.status == "ok"
    assert len(result.errors) == 0

    # Check entities: certificate, subdomains, ip
    types = [e.type for e in result.entities]
    assert "certificate" in types
    assert "subdomain" in types
    assert "ip" in types

    # Check wildcard attribute on certificate
    cert_entities = [e for e in result.entities if e.type == "certificate"]
    assert len(cert_entities) == 1
    assert cert_entities[0].attributes["wildcard"] is True

    # Check live vs dead subdomain attributes
    subdomains = {e.value: e.attributes for e in result.entities if e.type == "subdomain"}
    assert "api.example.com" in subdomains
    assert subdomains["api.example.com"]["live"] is True
    assert subdomains["mail.example.com"]["live"] is False


@pytest.mark.asyncio
async def test_ct_collector_empty(mock_resolver):
    mock_http = AsyncMock(spec=SafeHttpClient)
    mock_http.get.return_value = (200, {}, b"[]")

    collector = CTCollector(http_client=mock_http, resolver=mock_resolver)
    result = await collector.collect("nonexistent-empty-domain.test")

    assert result.collector == "ct"
    assert result.status == "ok"
    assert len(result.entities) == 0
    assert len(result.relations) == 0


@pytest.mark.asyncio
async def test_ct_collector_malformed(mock_resolver):
    mock_http = AsyncMock(spec=SafeHttpClient)
    mock_http.get.return_value = (200, {}, b"<html>Not JSON Error</html>")

    collector = CTCollector(http_client=mock_http, resolver=mock_resolver)
    result = await collector.collect("example.com")

    assert result.collector == "ct"
    assert result.status == "partial"
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_ct_collector_timeout_or_network_error(mock_resolver):
    mock_http = AsyncMock(spec=SafeHttpClient)
    mock_http.get.side_effect = TimeoutError("Connection to crt.sh timed out")

    collector = CTCollector(http_client=mock_http, resolver=mock_resolver)
    result = await collector.collect("example.com")

    assert result.collector == "ct"
    assert result.status == "partial"
    assert len(result.errors) == 1
    assert result.errors[0].code == "crtsh_timeout_or_error"
