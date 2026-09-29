"""Tests for SSRF Guard and Target Validation per Spec Rules S2 & S3."""

from unittest.mock import patch

import pytest
import respx

from app.core.ssrf_guard import (
    InvalidTargetError,
    SafeHttpClient,
    SSRFSecurityViolation,
    is_ip_allowed,
    resolve_and_validate_hostname,
    validate_outbound_url,
    validate_target_domain,
)


class TestTargetValidation:
    """Test public hostname target validation rules (S3)."""

    def test_valid_domain_names(self) -> None:
        assert validate_target_domain("example.com") == "example.com"
        assert validate_target_domain("sub.domain.co.uk") == "sub.domain.co.uk"
        assert validate_target_domain("TEST-CORP.ORG.") == "test-corp.org"
        assert validate_target_domain("  domain123.com  ") == "domain123.com"

    @pytest.mark.parametrize(
        "invalid_target",
        [
            "127.0.0.1",
            "10.0.0.5",
            "::1",
            "localhost",
            "test.local",
            "corp.internal",
            "server.lan",
            "https://example.com",
            "http://example.com",
            "user:password@example.com",
            "example.com:8080",
            "example.com/path",
            "example.com?query=1",
            "example.com#fragment",
            "",
            "   ",
            "no-tld",
        ],
    )
    def test_invalid_targets_rejected(self, invalid_target: str) -> None:
        with pytest.raises(InvalidTargetError):
            validate_target_domain(invalid_target)


class TestIpFiltering:
    """Test IP filtering against private, loopback, and metadata ranges (S2)."""

    @pytest.mark.parametrize(
        "safe_ip",
        [
            "8.8.8.8",
            "1.1.1.1",
            "93.184.216.34",
            "142.250.190.46",
            "2606:4700:4700::1111",
        ],
    )
    def test_public_ips_allowed(self, safe_ip: str) -> None:
        assert is_ip_allowed(safe_ip) is True

    @pytest.mark.parametrize(
        "dangerous_ip",
        [
            "127.0.0.1",
            "127.0.1.1",
            "::1",
            "10.0.0.1",
            "10.254.0.1",
            "172.16.0.1",
            "172.31.255.255",
            "192.168.1.1",
            "192.168.100.200",
            "169.254.169.254",  # Cloud Metadata
            "169.254.1.1",      # Link-local
            "fe80::1",          # IPv6 Link-local
            "fc00::1",          # IPv6 Unique Local Address
            "224.0.0.1",        # Multicast
            "0.0.0.0",          # Unspecified
            "100.64.0.1",       # Carrier-grade NAT
        ],
    )
    def test_prohibited_ips_rejected(self, dangerous_ip: str) -> None:
        assert is_ip_allowed(dangerous_ip) is False


class TestUrlValidation:
    """Test URL parsing, scheme restrictions, and port whitelist."""

    def test_allowed_urls(self) -> None:
        scheme, host, port = validate_outbound_url("https://example.com")
        assert scheme == "https"
        assert host == "example.com"
        assert port == 443

        scheme, host, port = validate_outbound_url("http://example.com:80/path")
        assert scheme == "http"
        assert port == 80

    @pytest.mark.parametrize(
        "forbidden_url",
        [
            "ftp://example.com",
            "file:///etc/passwd",
            "gopher://example.com",
            "http://user:pass@example.com",
            "https://example.com:22",
            "https://example.com:8080",
            "http://example.com:21",
        ],
    )
    def test_forbidden_urls_raise_security_violation(self, forbidden_url: str) -> None:
        with pytest.raises(SSRFSecurityViolation):
            validate_outbound_url(forbidden_url)


class TestSafeHttpClient:
    """Test SafeHttpClient DNS resolution, redirects, and size capping."""

    @pytest.mark.asyncio
    async def test_resolve_localhost_raises(self) -> None:
        with pytest.raises(SSRFSecurityViolation, match="localhost are blocked"):
            await resolve_and_validate_hostname("localhost")

    @pytest.mark.asyncio
    async def test_host_resolving_to_private_ip_raises(self) -> None:
        mock_addrinfo = [(2, 1, 6, "", ("192.168.1.10", 0))]
        with patch("asyncio.base_events.BaseEventLoop.getaddrinfo", return_value=mock_addrinfo):
            with pytest.raises(SSRFSecurityViolation, match="resolved to prohibited IP"):
                await resolve_and_validate_hostname("internal.example.com")

    @pytest.mark.asyncio
    async def test_safe_get_successful(self) -> None:
        client = SafeHttpClient(timeout=5.0)
        mock_addrinfo = [(2, 1, 6, "", ("93.184.216.34", 0))]

        with patch("asyncio.base_events.BaseEventLoop.getaddrinfo", return_value=mock_addrinfo):
            with respx.mock:
                respx.get("https://example.com/").respond(
                    status_code=200,
                    headers={"Server": "nginx"},
                    content=b"<html>Hello OSINT</html>",
                )
                status, headers, content = await client.get("https://example.com/")
                assert status == 200
                assert headers["server"] == "nginx"
                assert content == b"<html>Hello OSINT</html>"

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_blocked(self) -> None:
        client = SafeHttpClient(timeout=5.0)

        # First resolution: public IP (93.184.216.34), second resolution: private IP (10.0.0.1)
        dns_calls = [
            [(2, 1, 6, "", ("93.184.216.34", 0))],
            [(2, 1, 6, "", ("10.0.0.1", 0))],
        ]

        with patch("asyncio.base_events.BaseEventLoop.getaddrinfo", side_effect=dns_calls):
            with respx.mock:
                respx.get("https://example.com/").respond(
                    status_code=302,
                    headers={"Location": "https://internal-server.com/"},
                )
                with pytest.raises(SSRFSecurityViolation, match="resolved to prohibited IP"):
                    await client.get("https://example.com/")

    @pytest.mark.asyncio
    async def test_response_size_capped_at_2mb(self) -> None:
        client = SafeHttpClient(timeout=5.0)
        mock_addrinfo = [(2, 1, 6, "", ("93.184.216.34", 0))]
        giant_payload = b"A" * (3 * 1024 * 1024)  # 3 MB

        with patch("asyncio.base_events.BaseEventLoop.getaddrinfo", return_value=mock_addrinfo):
            with respx.mock:
                respx.get("https://example.com/").respond(
                    status_code=200,
                    content=giant_payload,
                )
                status, headers, content = await client.get("https://example.com/")
                assert status == 200
                assert len(content) == 2 * 1024 * 1024  # Capped at exactly 2 MB
