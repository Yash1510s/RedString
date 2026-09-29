"""Tests for DNS Collector and Mail Provider heuristics."""

from unittest.mock import patch

import pytest

from app.collectors.dns import DNSCollector, detect_mail_provider
from app.models.schemas import EntityType, RelationType


class TestMailProviderDetection:
    """Test heuristic identification of mail providers from MX hostnames."""

    def test_google_workspace_detected(self) -> None:
        result = detect_mail_provider("aspmx.l.google.com")
        assert result is not None
        assert result[0] == "google"
        assert result[1] == "Google Workspace"

    def test_microsoft_365_detected(self) -> None:
        result = detect_mail_provider("example-com.mail.protection.outlook.com")
        assert result is not None
        assert result[0] == "microsoft"
        assert result[1] == "Microsoft 365"

    def test_protonmail_detected(self) -> None:
        result = detect_mail_provider("mail.protonmail.ch")
        assert result is not None
        assert result[0] == "proton"

    def test_unknown_provider_returns_none(self) -> None:
        assert detect_mail_provider("mail.mycustomprivateinternal.org") is None


class TestDNSCollector:
    """Test DNS collection, entity generation, and evidence attachment with mocked DNS answers."""

    @pytest.mark.asyncio
    async def test_complete_dns_collection(self) -> None:
        collector = DNSCollector()

        # Mock answers for different DNS queries
        async def mock_query(domain: str, rtype: str) -> list[str]:
            if rtype == "A" and domain == "example.com":
                return ["93.184.216.34"]
            if rtype == "AAAA" and domain == "example.com":
                return ["2606:2800:220:1:248:1893:25c8:1946"]
            if rtype == "NS":
                return ["a.iana-servers.net", "b.iana-servers.net"]
            if rtype == "MX":
                return ["10 aspmx.l.google.com."]
            if rtype == "TXT" and domain == "example.com":
                return ["v=spf1 -all", "google-site-verification=abc"]
            if rtype == "TXT" and domain == "_dmarc.example.com":
                return ["v=DMARC1; p=reject; rua=mailto:dmarc@example.com"]
            return []

        with patch.object(collector, "_query_record", side_effect=mock_query):
            result = await collector.collect("example.com")

            assert result.status == "ok"
            assert result.collector == "dns"
            assert len(result.entities) > 0
            assert len(result.relations) > 0

            # Check entities by type
            entity_types = {e.type for e in result.entities}
            assert EntityType.ip in entity_types
            assert EntityType.nameserver in entity_types
            assert EntityType.mail_provider in entity_types

            # Check IP entities
            ips = [e.value for e in result.entities if e.type == EntityType.ip]
            assert "93.184.216.34" in ips
            assert "2606:2800:220:1:248:1893:25c8:1946" in ips

            # Check Mail Provider
            mail_providers = [
                e.value for e in result.entities if e.type == EntityType.mail_provider
            ]
            assert "Google Workspace" in mail_providers

            # Check relations
            relation_types = {r.type for r in result.relations}
            assert RelationType.RESOLVES_TO in relation_types
            assert RelationType.USES_NS in relation_types
            assert RelationType.USES_MAIL in relation_types

            # Check evidence completeness
            for ent in result.entities:
                assert len(ent.evidence) >= 1
                assert ent.evidence[0].source_name == "dns"

            for rel in result.relations:
                assert len(rel.evidence) >= 1
                assert rel.evidence[0].source_name == "dns"
