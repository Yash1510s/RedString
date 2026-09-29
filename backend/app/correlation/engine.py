"""Correlation Engine implementing deterministic relationship derivation per Spec Section 8."""

import ipaddress
import logging
from collections import defaultdict
from typing import Any

from app.collectors.tech import load_cloud_ranges
from app.models.db_models import Entity, Evidence, Relation
from app.models.normalisation import utc_now

logger = logging.getLogger(__name__)


def elevate_confidence(current: str, distinct_sources_count: int) -> str:
    """Elevate confidence by one step if supported by 2+ independent sources."""
    if distinct_sources_count < 2:
        return current
    if current == "low":
        return "medium"
    return "high"


class CorrelationEngine:
    """Deterministic correlation engine for linking entities and elevating confidence."""

    def __init__(self) -> None:
        self.cloud_providers = load_cloud_ranges()

    def match_ip_cloud(self, ip_str: str) -> str | None:
        """Match an IP against known cloud provider ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return None

        for prov in self.cloud_providers:
            prov_name = str(prov.get("name", ""))
            for cidr in prov.get("cidrs", []):
                try:
                    if ip_obj in ipaddress.ip_network(cidr, strict=False):
                        return prov_name
                except ValueError:
                    continue
        return None

    def correlate(
        self,
        entities: list[Entity],
        relations: list[Relation],
        evidence_list: list[Evidence],
    ) -> dict[str, Any]:
        """Correlate entities, tag IP clusters, and construct Cytoscape-compatible graph."""
        # Map evidence by relation_id to count distinct sources
        rel_sources: dict[int, set[str]] = defaultdict(set)
        for ev in evidence_list:
            if ev.relation_id is not None:
                rel_sources[ev.relation_id].add(ev.source_name)

        # 1. Detect shared IP groups among domain / subdomain entities
        ip_to_hosts: dict[str, set[str]] = defaultdict(set)
        host_entities: dict[str, Entity] = {}

        for ent in entities:
            if ent.type in {"domain", "subdomain"}:
                host_entities[ent.value] = ent

        for rel in relations:
            if rel.type == "RESOLVES_TO" and rel.source and rel.target:
                # source is hostname, target is IP
                if rel.source.type in {"domain", "subdomain"} and rel.target.type == "ip":
                    ip_to_hosts[rel.target.value].add(rel.source.value)

        # Tag hostnames sharing an IP
        shared_groups: dict[str, str] = {}
        for ip_val, hosts in ip_to_hosts.items():
            if len(hosts) > 1:
                group_id = f"ip-group-{ip_val.replace('.', '-')}"
                for h in hosts:
                    shared_groups[h] = group_id

        # 2. Build Cytoscape nodes
        nodes: list[dict[str, Any]] = []
        node_id_map: dict[int, str] = {}

        for ent in entities:
            nid = f"e{ent.id}"
            node_id_map[ent.id] = nid

            attrs = dict(ent.attributes or {})
            if ent.value in shared_groups:
                attrs["shared_ip_group"] = shared_groups[ent.value]

            # Format finding ID (e.g. F-000012)
            finding_id = f"F-{ent.id:06d}"

            nodes.append(
                {
                    "data": {
                        "id": nid,
                        "entityId": ent.id,
                        "label": ent.value,
                        "type": ent.type,
                        "findingId": finding_id,
                        "attributes": attrs,
                    }
                }
            )

        # 3. Build Cytoscape edges with elevated confidence where applicable
        edges: list[dict[str, Any]] = []
        for rel in relations:
            sid = node_id_map.get(rel.source_id)
            tid = node_id_map.get(rel.target_id)
            if not sid or not tid:
                continue

            sources_count = len(rel_sources.get(rel.id, set()))
            final_conf = elevate_confidence(rel.confidence, sources_count)
            finding_id = f"R-{rel.id:06d}"

            edges.append(
                {
                    "data": {
                        "id": f"r{rel.id}",
                        "relationId": rel.id,
                        "source": sid,
                        "target": tid,
                        "type": rel.type,
                        "confidence": final_conf,
                        "findingId": finding_id,
                        "distinct_sources": list(rel_sources.get(rel.id, set())),
                    }
                }
            )

        now = utc_now().isoformat()
        return {
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "nodeCount": len(nodes),
                "edgeCount": len(edges),
                "generatedAt": now,
            },
        }
