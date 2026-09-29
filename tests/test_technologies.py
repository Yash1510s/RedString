from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.collectors.technologies import TechnologyCollector
from app.core.evidence import EvidenceStore


def test_technology_collector_structure():
    collector = TechnologyCollector()
    res = collector.collect("example.com")
    assert res["collector"] == "technology_detection"
    assert res["target"] == "example.com"
    assert "findings" in res
    assert "errors" in res


@patch("httpx.Client.get")
def test_technology_collector_header_detection(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.url = "https://example.com"
    mock_response.headers = httpx.Headers({"Server": "nginx/1.18.0", "X-Powered-By": "PHP/8.1.0"})
    mock_response.text = "<html><head></head><body>Hello</body></html>"
    mock_get.return_value = mock_response

    collector = TechnologyCollector()
    res = collector.collect("example.com")

    tech_names = [item["name"] for item in res["findings"]]
    assert "nginx" in tech_names
    assert "PHP" in tech_names


@patch("httpx.Client.get")
def test_technology_collector_html_meta_detection(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.url = "https://example.com"
    mock_response.headers = httpx.Headers({"Server": "cloudflare"})
    mock_response.text = '<html><head><meta name="generator" content="WordPress 6.4"></head><body><script src="/wp-content/themes/main.js"></script></body></html>'
    mock_get.return_value = mock_response

    collector = TechnologyCollector()
    res = collector.collect("example.com")

    tech_names = [item["name"] for item in res["findings"]]
    assert "WordPress 6.4" in tech_names or "WordPress" in tech_names
    assert "cloudflare" in tech_names


@patch("httpx.Client.get")
def test_technology_collector_network_error(mock_get):
    mock_get.side_effect = httpx.TimeoutException("Connection timed out")

    collector = TechnologyCollector()
    res = collector.collect("example.com")

    assert "http" in res["errors"]
    assert len(res["findings"]) == 0


def test_evidence_ingestion_for_technologies():
    mock_tech_data = {
        "collector": "technology_detection",
        "target": "example.com",
        "findings": [
            {"name": "nginx", "basis": "Server HTTP header ('Server: nginx')"},
            {"name": "React", "basis": "HTML indicator ('react' reference)"},
        ],
        "errors": {},
    }

    store = EvidenceStore()
    items = store.ingest_technology_results(mock_tech_data)

    assert len(items) == 2
    assert items[0].finding == "nginx"
    assert items[0].entity_type == "TECHNOLOGY"
    assert items[0].source == "HTTP_ANALYSIS"

    assert items[1].finding == "React"
    assert items[1].entity_type == "TECHNOLOGY"
