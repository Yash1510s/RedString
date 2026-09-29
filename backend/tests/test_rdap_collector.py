"""Tests for RDAP Collector and Safety Rule S6 personal data stripping."""

import json
from unittest.mock import AsyncMock

import pytest

from app.collectors.rdap import RDAPCollector, sanitize_rdap_payload
from app.models.schemas import EntityType


class TestRDAPSanitization:
    """Test Rule S6: No personal profiling, stripping registrant PII."""

    def test_strip_personal_contact_fields(self) -> None:
        raw_payload = {
            "objectClassName": "domain",
            "handle": "2138514_DOMAIN_COM-VRSN",
            "name": "John Doe",  # Must be stripped
            "email": "private@owner.com",  # Must be stripped
            "entities": [
                {
                    "roles": ["registrant"],
                    "handle": "CR30129",
                    "vcardArray": [
                        "vcard",
                        [
                            ["version", {}, "text", "4.0"],
                            ["fn", {}, "text", "Secret Person"],  # Must be redacted
                            ["email", {}, "text", "person@secret.com"],  # Must be redacted
                            ["org", {}, "text", "Acme Corporation Inc"],  # Must be preserved
                        ],
                    ],
                }
            ],
        }

        sanitized = sanitize_rdap_payload(raw_payload)
        assert "name" not in sanitized
        assert "email" not in sanitized

        # Check vcardArray
        registrant_ent = sanitized["entities"][0]
        vcard_props = registrant_ent["vcardArray"][1]
        prop_names = [p[0] for p in vcard_props]
        assert "version" in prop_names
        assert "org" in prop_names
        # fn must be redacted to text REDACTED_WITHHELD
        fn_prop = next(p for p in vcard_props if p[0] == "fn")
        assert fn_prop[3] == "REDACTED_WITHHELD"


class TestRDAPCollector:
    """Test RDAP collection with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_successful_rdap_collection(self) -> None:
        mock_http = AsyncMock()
        rdap_sample = {
            "objectClassName": "domain",
            "ldhName": "example.com",
            "status": ["clientTransferProhibited"],
            "events": [
                {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
                {"eventAction": "expiration", "eventDate": "2027-08-13T04:00:00Z"},
            ],
            "entities": [
                {
                    "roles": ["registrar"],
                    "handle": "292",
                    "vcardArray": [
                        "vcard",
                        [
                            ["version", {}, "text", "4.0"],
                            ["fn", {}, "text", "Example Registrar LLC"],
                        ],
                    ],
                }
            ],
            "nameservers": [{"ldhName": "a.iana-servers.net"}],
        }

        mock_http.get.return_value = (200, {}, json.dumps(rdap_sample).encode())

        collector = RDAPCollector(http_client=mock_http)
        result = await collector.collect("example.com")

        assert result.status == "ok"
        assert result.collector == "rdap"
        assert len(result.entities) >= 1

        domain_ent = next(e for e in result.entities if e.type == EntityType.domain)
        assert domain_ent.attributes.get("registrar") == "Example Registrar LLC"
        assert domain_ent.attributes.get("registered_at") == "1995-08-14T04:00:00Z"
        assert domain_ent.attributes.get("expires_at") == "2027-08-13T04:00:00Z"

    @pytest.mark.asyncio
    async def test_rdap_upstream_failure_handles_gracefully(self) -> None:
        mock_http = AsyncMock()
        mock_http.get.return_value = (503, {}, b"Service Unavailable")

        collector = RDAPCollector(http_client=mock_http)
        result = await collector.collect("example.com")

        assert result.status == "partial"
        assert len(result.errors) == 1
        assert result.errors[0].code == "upstream_error"
