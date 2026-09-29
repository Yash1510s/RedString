from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.collectors.certificates import CertificateCollector
from app.core.evidence import EvidenceStore


@patch("httpx.Client.get")
def test_certificate_collector_structure(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    collector = CertificateCollector()
    res = collector.collect("example.com")
    assert res["collector"] == "certificate_transparency"
    assert res["target"] == "example.com"
    assert "findings" in res
    assert "errors" in res


@patch("httpx.Client.get")
def test_certificate_collector_mocked_response(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"name_value": "example.com\nwww.example.com"},
        {"name_value": "*.api.example.com"},
        {"name_value": "unrelated.org"},
    ]
    mock_get.return_value = mock_response

    collector = CertificateCollector()
    res = collector.collect("example.com")

    # Should normalize *.api.example.com to api.example.com and filter out unrelated.org
    assert "example.com" in res["findings"]
    assert "www.example.com" in res["findings"]
    assert "api.example.com" in res["findings"]
    assert "unrelated.org" not in res["findings"]


@patch.object(CertificateCollector, "_query_crt_sh")
def test_certificate_collector_timeout_handling(mock_query):
    mock_query.side_effect = httpx.TimeoutException("Connection timed out")

    collector = CertificateCollector()
    res = collector.collect("example.com")

    assert "crt.sh" in res["errors"]
    assert "timed out" in res["errors"]["crt.sh"]



def test_evidence_ingestion_for_certificates():
    mock_cert_data = {
        "collector": "certificate_transparency",
        "target": "example.com",
        "findings": ["example.com", "sub.example.com"],
        "errors": {},
    }

    store = EvidenceStore()
    items = store.ingest_certificate_results(mock_cert_data)

    assert len(items) == 2
    assert items[0].finding == "example.com"
    assert items[0].entity_type == "DOMAIN"
    assert items[0].source == "CERTIFICATE_TRANSPARENCY"

    assert items[1].finding == "sub.example.com"
    assert items[1].entity_type == "SUBDOMAIN"
