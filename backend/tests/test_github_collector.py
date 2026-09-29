"""Tests for GitHub Collector and Safety Rule S5 public metadata only."""

import json
from unittest.mock import AsyncMock

import pytest

from app.collectors.github import GitHubCollector
from app.core.ssrf_guard import SafeHttpClient


@pytest.mark.asyncio
async def test_github_collector_success():
    mock_http = AsyncMock(spec=SafeHttpClient)

    search_payload = {
        "items": [
            {
                "full_name": "example-org/example-repo",
                "homepage": "https://example.com",
                "description": "Official open source SDK for example.com",
                "stargazers_count": 1250,
                "forks_count": 85,
                "language": "TypeScript",
                "html_url": "https://github.com/example-org/example-repo",
                "owner": {
                    "login": "example-org",
                    "type": "Organization",
                    "html_url": "https://github.com/example-org",
                },
            }
        ]
    }

    contrib_payload = [
        {
            "login": "octocat",
            "contributions": 142,
            "html_url": "https://github.com/octocat",
            "avatar_url": "https://avatars.githubusercontent.com/u/1",
        }
    ]

    mock_http.get.side_effect = [
        (200, {}, json.dumps(search_payload).encode("utf-8")),
        (200, {}, json.dumps(contrib_payload).encode("utf-8")),
    ]

    collector = GitHubCollector(http_client=mock_http)
    result = await collector.collect("example.com")

    assert result.collector == "github"
    assert result.status == "ok"
    assert len(result.errors) == 0

    types = [e.type for e in result.entities]
    assert "repository" in types
    assert "organization" in types
    assert "person" in types

    # Check that person entity has public contributions and login
    people = [e for e in result.entities if e.type == "person"]
    assert len(people) == 1
    assert people[0].value == "octocat"
    assert people[0].attributes["contributions"] == 142

    # Check relations: person -> CONTRIBUTED_TO -> repository
    contrib_rels = [r for r in result.relations if r.type == "CONTRIBUTED_TO"]
    assert len(contrib_rels) == 1
    assert contrib_rels[0].source == ("person", "octocat")
    assert contrib_rels[0].target == ("repository", "example-org/example-repo")


@pytest.mark.asyncio
async def test_github_collector_rate_limit():
    mock_http = AsyncMock(spec=SafeHttpClient)
    mock_http.get.return_value = (
        403,
        {"x-ratelimit-remaining": "0"},
        b'{"message": "rate limit exceeded"}',
    )

    collector = GitHubCollector(http_client=mock_http)
    result = await collector.collect("example.com")

    assert result.collector == "github"
    assert result.status == "partial"
    assert len(result.errors) == 1
    assert result.errors[0].code == "rate_limited"
