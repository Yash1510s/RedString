import pytest
from rich.tree import Tree
from app.core.models import Relationship
from app.graph.builder import GraphBuilder


def test_graph_builder_empty():
    builder = GraphBuilder()
    tree = builder.build_tree("example.com", [])

    assert isinstance(tree, Tree)
    assert "example.com" in str(tree.label)


def test_graph_builder_with_relationships():
    relationships = [
        Relationship(id="REL-001", source_entity="example.com", relationship_type="HAS_SUBDOMAIN", target_entity="api.example.com", evidence_id="E-001"),
        Relationship(id="REL-002", source_entity="example.com", relationship_type="RESOLVES_TO", target_entity="93.184.216.34", evidence_id="E-002"),
        Relationship(id="REL-003", source_entity="example.com", relationship_type="USES_TECHNOLOGY", target_entity="nginx", evidence_id="E-003"),
    ]

    builder = GraphBuilder()
    tree = builder.build_tree("example.com", relationships)

    assert isinstance(tree, Tree)
    assert len(tree.children) == 3

    branch_labels = [str(child.label) for child in tree.children]
    assert any("HAS_SUBDOMAIN" in b for b in branch_labels)
    assert any("RESOLVES_TO" in b for b in branch_labels)
    assert any("USES_TECHNOLOGY" in b for b in branch_labels)
