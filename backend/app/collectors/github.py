"""GitHub Metadata and Public Contributors Collector per Spec Section 6 & Safety Rule S5."""

import json
import logging
import os
import time
from typing import Any

from app.core.ssrf_guard import SafeHttpClient
from app.models.normalisation import normalise_hostname, utc_now
from app.models.schemas import (
    CollectorError,
    CollectorResult,
    Confidence,
    EntityIn,
    EntityType,
    EvidenceIn,
    RelationIn,
    RelationType,
)

logger = logging.getLogger(__name__)

COLLECTOR_NAME = "github"
COLLECTOR_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 10.0
GITHUB_API_BASE = "https://api.github.com"
MAX_REPOSITORIES = 10
MAX_CONTRIBUTORS_PER_REPO = 5


class GitHubCollector:
    """Passively queries GitHub public API for repositories, organizations, and top contributors."""

    name: str = COLLECTOR_NAME
    version: str = COLLECTOR_VERSION
    timeout_s: int = int(DEFAULT_TIMEOUT)

    def __init__(self, http_client: SafeHttpClient | None = None) -> None:
        self.http_client = http_client or SafeHttpClient(timeout=DEFAULT_TIMEOUT)
        self.api_token = os.getenv("GITHUB_TOKEN")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RedString-OSINT-Passive-Scanner/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def collect(self, target: str) -> CollectorResult:
        """Find public repositories referencing the domain and associated people."""
        start_time = time.perf_counter()
        clean_domain = normalise_hostname(target)
        now = utc_now()

        entities: list[EntityIn] = []
        relations: list[RelationIn] = []
        errors: list[CollectorError] = []

        search_url = (
            f"{GITHUB_API_BASE}/search/repositories?q={clean_domain}"
            f"&sort=stars&order=desc&per_page={MAX_REPOSITORIES}"
        )

        repo_items: list[dict[str, Any]] = []

        try:
            status_code, resp_headers, body = await self.http_client.get(
                search_url,
                headers=self._get_headers(),
            )

            if status_code == 200:
                data = json.loads(body.decode("utf-8", errors="replace"))
                repo_items = data.get("items", [])
            elif status_code == 403 or status_code == 429:
                errors.append(
                    CollectorError(
                        code="rate_limited",
                        message="GitHub rate limit reached. Set GITHUB_TOKEN to raise limit.",
                        retryable=True,
                    )
                )
            else:
                errors.append(
                    CollectorError(
                        code="github_api_error",
                        message=f"GitHub API returned HTTP {status_code}",
                        retryable=True,
                    )
                )
        except Exception as exc:
            logger.warning("GitHub repository search failed: %s", exc)
            errors.append(
                CollectorError(
                    code="github_network_error",
                    message=f"GitHub API request failed: {exc}",
                    retryable=True,
                )
            )

        seen_repos: set[str] = set()
        seen_orgs: set[str] = set()
        seen_people: set[str] = set()

        for item in repo_items:
            full_name = item.get("full_name")
            if not full_name or full_name in seen_repos:
                continue
            seen_repos.add(full_name)

            homepage = (item.get("homepage") or "").lower()
            description = item.get("description") or ""
            stars = item.get("stargazers_count", 0)
            forks = item.get("forks_count", 0)
            html_url = item.get("html_url", "")
            language = item.get("language")

            # Determine match confidence per Spec Section 6
            if clean_domain in homepage:
                conf = Confidence.high
                match_basis = "homepage_exact_match"
            elif clean_domain in description.lower():
                conf = Confidence.medium
                match_basis = "description_match"
            else:
                conf = Confidence.low
                match_basis = "search_relevance"

            ev_repo = EvidenceIn(
                source_name=self.name,
                source_ref=html_url,
                raw={
                    "full_name": full_name,
                    "stars": stars,
                    "forks": forks,
                    "language": language,
                    "homepage": homepage,
                    "match_basis": match_basis,
                },
                collected_at=now,
                collector_version=self.version,
            )

            # Record repository entity
            entities.append(
                EntityIn(
                    type=EntityType.repository,
                    value=full_name,
                    attributes={
                        "stars": stars,
                        "forks": forks,
                        "language": language,
                        "html_url": html_url,
                        "description": description[:200],
                        "match_basis": match_basis,
                    },
                    evidence=[ev_repo],
                )
            )

            relations.append(
                RelationIn(
                    source=(EntityType.repository, full_name),
                    target=(EntityType.domain, clean_domain),
                    type=RelationType.MENTIONS,
                    confidence=conf,
                    evidence=[ev_repo],
                )
            )

            # Owner organization or user
            owner_data = item.get("owner")
            if isinstance(owner_data, dict):
                owner_login = owner_data.get("login", "")
                owner_type = owner_data.get("type", "Organization")
                owner_url = owner_data.get("html_url", "")

                if owner_login and owner_login not in seen_orgs:
                    seen_orgs.add(owner_login)
                    ent_type = (
                        EntityType.organization
                        if owner_type.lower() == "organization"
                        else EntityType.person
                    )

                    ev_owner = EvidenceIn(
                        source_name=self.name,
                        source_ref=owner_url,
                        raw={"login": owner_login, "type": owner_type, "url": owner_url},
                        collected_at=now,
                        collector_version=self.version,
                    )

                    entities.append(
                        EntityIn(
                            type=ent_type,
                            value=owner_login,
                            attributes={
                                "login": owner_login,
                                "type": owner_type,
                                "html_url": owner_url,
                                "role": "Repository Owner",
                            },
                            evidence=[ev_owner],
                        )
                    )

                    rel_type = (
                        RelationType.OWNS
                        if ent_type == EntityType.organization
                        else RelationType.CONTRIBUTED_TO
                    )
                    relations.append(
                        RelationIn(
                            source=(ent_type, owner_login),
                            target=(EntityType.repository, full_name),
                            type=rel_type,
                            confidence=Confidence.high,
                            evidence=[ev_owner],
                        )
                    )

            # Fetch top ranking contributors / people (Cap to top 3 repos)
            if len(seen_repos) <= 3:
                contrib_url = (
                    f"{GITHUB_API_BASE}/repos/{full_name}/contributors"
                    f"?per_page={MAX_CONTRIBUTORS_PER_REPO}"
                )
                try:
                    c_status, _, c_body = await self.http_client.get(
                        contrib_url,
                        headers=self._get_headers(),
                    )
                    if c_status == 200:
                        contribs = json.loads(c_body.decode("utf-8", errors="replace"))
                        if isinstance(contribs, list):
                            for person in contribs[:MAX_CONTRIBUTORS_PER_REPO]:
                                p_login = person.get("login")
                                p_contributions = person.get("contributions", 0)
                                p_url = person.get("html_url", "")
                                p_avatar = person.get("avatar_url", "")

                                if p_login and p_login not in seen_people:
                                    seen_people.add(p_login)
                                    ev_person = EvidenceIn(
                                        source_name=self.name,
                                        source_ref=p_url,
                                        raw={
                                            "login": p_login,
                                            "contributions": p_contributions,
                                            "repository": full_name,
                                        },
                                        collected_at=now,
                                        collector_version=self.version,
                                    )

                                    entities.append(
                                        EntityIn(
                                            type=EntityType.person,
                                            value=p_login,
                                            attributes={
                                                "login": p_login,
                                                "contributions": p_contributions,
                                                "html_url": p_url,
                                                "avatar_url": p_avatar,
                                                "role": "Top Contributor",
                                                "associated_repo": full_name,
                                            },
                                            evidence=[ev_person],
                                        )
                                    )

                                    relations.append(
                                        RelationIn(
                                            source=(EntityType.person, p_login),
                                            target=(EntityType.repository, full_name),
                                            type=RelationType.CONTRIBUTED_TO,
                                            confidence=Confidence.high,
                                            evidence=[ev_person],
                                        )
                                    )
                except Exception as c_err:
                    logger.debug("Contributors query failed for %s: %s", full_name, c_err)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        status = "ok" if (entities or relations) else ("partial" if errors else "ok")

        return CollectorResult(
            collector=self.name,
            status=status,
            entities=entities,
            relations=relations,
            errors=errors,
            duration_ms=duration_ms,
        )
