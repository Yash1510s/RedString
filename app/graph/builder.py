from typing import List
from rich.tree import Tree
from app.core.models import Relationship


class GraphBuilder:
    """
    Builds a text-based terminal relationship tree using Rich Tree.
    """

    REL_COLOR_MAP = {
        "HAS_SUBDOMAIN": "cyan",
        "RESOLVES_TO": "green",
        "USES_NAMESERVER": "yellow",
        "USES_MAILSERVER": "magenta",
        "USES_TECHNOLOGY": "bright_blue",
        "HAS_CNAME": "bright_cyan",
        "ASSOCIATED_WITH": "white",
    }

    def build_tree(self, target_domain: str, relationships: List[Relationship]) -> Tree:
        """
        Constructs a Rich Tree object rooted at target_domain.
        """
        root_label = f"[bold white on blue] {target_domain} [/bold white on blue]"
        tree = Tree(root_label, guide_style="bright_blue")

        if not relationships:
            tree.add("[dim]No entity relationships discovered.[/dim]")
            return tree

        # Group relationships by type
        grouped: dict = {}
        for rel in relationships:
            grouped.setdefault(rel.relationship_type, []).append(rel)

        for rel_type, rel_list in grouped.items():
            color = self.REL_COLOR_MAP.get(rel_type, "white")
            branch_label = f"[bold {color}]{rel_type}[/bold {color}] ([dim]{len(rel_list)}[/dim])"
            branch = tree.add(branch_label)

            for rel in rel_list:
                node_text = f"[white]{rel.target_entity}[/white] [dim]({rel.evidence_id})[/dim]"
                branch.add(node_text)

        return tree
