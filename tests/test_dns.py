from unittest.mock import MagicMock, patch
import dns.resolver
import pytest
from app.collectors.dns import DNSCollector


def test_dns_collector_structure():
    collector = DNSCollector()
    res = collector.collect("example.com")
    assert res["collector"] == "dns"
    assert res["target"] == "example.com"
    assert "findings" in res
    assert "errors" in res
    for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
        assert rtype in res["findings"]


@patch("dns.resolver.Resolver.resolve")
def test_dns_collector_mocked_records(mock_resolve):
    # Mock A record
    mock_a = MagicMock()
    mock_a.to_text.return_value = "93.184.216.34"

    # Mock MX record
    mock_mx = MagicMock()
    mock_mx.preference = 10
    mock_mx.exchange.to_text.return_value = "mail.example.com."

    def side_effect(domain, rtype):
        if rtype == "A":
            return [mock_a]
        elif rtype == "MX":
            return [mock_mx]
        else:
            raise dns.resolver.NoAnswer()

    mock_resolve.side_effect = side_effect

    collector = DNSCollector()
    res = collector.collect("example.com")

    assert res["findings"]["A"] == ["93.184.216.34"]
    assert res["findings"]["MX"] == ["10 mail.example.com"]
    assert res["findings"]["NS"] == []


@patch("dns.resolver.Resolver.resolve")
def test_dns_collector_nxdomain(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NXDOMAIN()

    collector = DNSCollector()
    res = collector.collect("nonexistent-domain-12345.com")

    assert "domain" in res["errors"]
    assert "NXDOMAIN" in res["errors"]["domain"]
