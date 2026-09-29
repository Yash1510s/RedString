from typing import List
from rich.tree import Tree
from app.core.models import Relationship


class GraphBuilder:
    """
    Builds a text-based terminal relationship tree using Rich Tree.
    Uses high-contrast colors legible on both dark and light terminal themes.
    """

    REL_COLOR_MAP = {
        "HAS_SUBDOMAIN": "bright_cyan",
        "RESOLVES_TO": "bright_green",
        "USES_NAMESERVER": "bright_yellow",
        "USES_MAILSERVER": "bright_magenta",
        "USES_TECHNOLOGY": "bright_blue",
        "HAS_CNAME": "cyan",
        "ASSOCIATED_WITH": "bright_white",
    }

    def build_tree(self, target_domain: str, relationships: List[Relationship]) -> Tree:
        """
        Constructs a Rich Tree object rooted at target_domain.
        """
        root_label = f"[bold bright_white on cyan] {target_domain} [/bold bright_white on cyan]"
        tree = Tree(root_label, guide_style="bright_cyan")

        if not relationships:
            tree.add("[yellow]No entity relationships discovered.[/yellow]")
            return tree

        # Group relationships by type
        grouped: dict = {}
        for rel in relationships:
            grouped.setdefault(rel.relationship_type, []).append(rel)

        for rel_type, rel_list in grouped.items():
            color = self.REL_COLOR_MAP.get(rel_type, "bright_white")
            branch_label = f"[bold {color}]{rel_type}[/bold {color}] ([bright_yellow]{len(rel_list)}[/bright_yellow])"
            branch = tree.add(branch_label)

            for rel in rel_list:
                node_text = f"[bright_white]{rel.target_entity}[/bright_white] [yellow]({rel.evidence_id})[/yellow]"
                branch.add(node_text)

        return tree
