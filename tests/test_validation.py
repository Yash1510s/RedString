import pytest
from app.core.validation import validate_domain


def test_valid_domains():
    valid_list = ["example.com", "sub.example.com", "my-domain.org", "TEST.CO.UK"]
    for d in valid_list:
        is_valid, normalized = validate_domain(d)
        assert is_valid, f"Expected {d} to be valid"
        assert normalized == d.lower()


def test_invalid_domains_urls():
    invalid_urls = [
        "http://example.com",
        "https://example.com/path",
        "example.com:8080",
        "user:pass@example.com",
        "example.com?query=1",
    ]
    for url in invalid_urls:
        is_valid, msg = validate_domain(url)
        assert not is_valid, f"Expected {url} to be invalid"


def test_invalid_ip_addresses():
    ips = ["192.168.1.1", "8.8.8.8", "127.0.0.1"]
    for ip in ips:
        is_valid, msg = validate_domain(ip)
        assert not is_valid, f"Expected IP {ip} to be rejected"
        assert "IP address" in msg


def test_invalid_local_hosts():
    local_hosts = ["localhost", "server.local", "test.localhost"]
    for host in local_hosts:
        is_valid, msg = validate_domain(host)
        assert not is_valid, f"Expected {host} to be rejected"
