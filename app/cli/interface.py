import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text

from app.core.models import Investigation
from app.core.validation import validate_domain

console = Console()


def print_banner():
    """
    Renders a clean, high-contrast Rich banner.
    """
    banner_text = Text("OSINT INVESTIGATION COPILOT", style="bold bright_white on cyan", justify="center")
    subtext = Text("Passive Public-Source Intelligence Collector", style="bold bright_white", justify="center")
    
    panel_content = Text()
    panel_content.append(banner_text)
    panel_content.append("\n")
    panel_content.append(subtext)
    
    console.print(Panel(panel_content, border_style="cyan", padding=(0, 2)))


def print_investigation_header(investigation: Investigation):
    """
    Displays the initialized investigation details.
    """
    info_text = (
        f"[bold bright_cyan]Investigation ID:[/bold bright_cyan] [bold white]{investigation.id}[/bold white]\n"
        f"[bold bright_cyan]Target:[/bold bright_cyan]           [bold bright_yellow]{investigation.target}[/bold bright_yellow]\n"
        f"[bold bright_cyan]Target Type:[/bold bright_cyan]      {investigation.target_type}\n"
        f"[bold bright_cyan]Started At:[/bold bright_cyan]       {investigation.created_at}\n"
        f"[bold bright_cyan]Status:[/bold bright_cyan]           [bold bright_green]{investigation.status}[/bold bright_green]"
    )
    console.print(Panel(info_text, title="[bold white]Investigation Initialized[/bold white]", border_style="cyan", padding=(0, 2)))


def get_target_domain_interactively() -> str:
    """
    Prompts the user interactively for a domain target with validation.
    """
    while True:
        try:
            raw_input = Prompt.ask("\n[bold bright_yellow]Enter target domain[/bold bright_yellow] (e.g. example.com)").strip()
            if not raw_input:
                continue
            is_valid, result = validate_domain(raw_input)
            if is_valid:
                return result
            else:
                console.print(f"[bold red]Error:[/bold red] {result}")
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Investigation cancelled by user.[/bold yellow]")
            sys.exit(0)


def print_error(message: str):
    """
    Prints an error message in a styled format.
    """
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_dns_findings(dns_data: dict):
    """
    Renders DNS findings in readable Rich panels and tables.
    """
    findings = dns_data.get("findings", {})
    errors = dns_data.get("errors", {})

    console.print("\n[bold bright_cyan]=== DNS INTELLIGENCE ===[/bold bright_cyan]\n")

    if errors.get("domain"):
        console.print(f"[bold red]![/bold red] {errors['domain']}")
        return

    has_records = False
    for rtype, records in findings.items():
        if records:
            has_records = True
            console.print(f"[bold bright_yellow]{rtype} Records[/bold bright_yellow] ({len(records)})")
            for record in records:
                console.print(f"  • [bright_white]{record}[/bright_white]")
            console.print()

    if not has_records:
        console.print("[yellow]No DNS records resolved for this target.[/yellow]")

    if errors:
        for rtype, err in errors.items():
            console.print(f"[yellow]Warning ({rtype}): {err}[/yellow]")


def print_evidence_table(evidence_store):
    """
    Renders structured evidence items in a clean Rich table.
    """
    from rich.table import Table

    items = evidence_store.get_all()
    if not items:
        return

    table = Table(title="EVIDENCE PROVENANCE", border_style="cyan", header_style="bold bright_cyan")
    table.add_column("ID", style="bold bright_yellow", width=8)
    table.add_column("Finding", style="bright_white", min_width=20)
    table.add_column("Entity Type", style="bold bright_green")
    table.add_column("Source", style="bold bright_magenta")
    table.add_column("Source Reference", style="white")

    for ev in items:
        table.add_row(
            ev.id,
            ev.finding,
            ev.entity_type,
            ev.source,
            ev.source_reference,
        )

    console.print()
    console.print(table)


def print_certificate_findings(cert_data: dict):
    """
    Renders Certificate Transparency findings in Rich formatted sections.
    """
    findings = cert_data.get("findings", [])
    errors = cert_data.get("errors", {})

    console.print("\n[bold bright_magenta]=== CERTIFICATE INTELLIGENCE ===[/bold bright_magenta]\n")

    if errors.get("crt.sh"):
        console.print(f"[yellow]Warning (Certificate Transparency): {errors['crt.sh']}[/yellow]")
        if not findings:
            return

    if findings:
        console.print(f"[bold bright_cyan]Publicly Observable Hostnames[/bold bright_cyan] ({len(findings)})")
        display_limit = 15
        for hostname in findings[:display_limit]:
            console.print(f"  • [bright_white]{hostname}[/bright_white]")
        
        if len(findings) > display_limit:
            console.print(f"  [yellow]... and {len(findings) - display_limit} more hostnames (recorded in evidence).[/yellow]")

        console.print("\n[italic white]* Publicly observable hostnames identified through Certificate Transparency.[/italic white]\n")
    else:
        console.print("[yellow]No public Certificate Transparency hostnames observed for this target.[/yellow]\n")


def print_technology_findings(tech_data: dict):
    """
    Renders passive HTTP/HTML Technology findings in Rich formatted sections.
    """
    findings = tech_data.get("findings", [])
    errors = tech_data.get("errors", {})

    console.print("\n[bold bright_yellow]=== TECHNOLOGY INTELLIGENCE ===[/bold bright_yellow]\n")

    if errors.get("http"):
        console.print(f"[yellow]Warning (HTTP Analysis): {errors['http']}[/yellow]")
        if not findings:
            return

    if findings:
        console.print(f"[bold bright_cyan]Observed Web Technologies[/bold bright_cyan] ({len(findings)})")
        for item in findings:
            name = item.get("name", "Unknown")
            basis = item.get("basis", "")
            console.print(f"  • [bright_white]{name}[/bright_white] [white]— {basis}[/white]")
        console.print()

    else:
        console.print("[yellow]No web technologies detected from passive HTTP/HTML inspection.[/yellow]\n")


def print_normalized_findings_summary(findings: list):
    """
    Renders a summary panel of normalized findings grouped by entity type.
    """
    if not findings:
        return

    from collections import Counter
    counts = Counter(f.entity_type for f in findings)

    summary_text = (
        f"[bold bright_green][+] Normalized Findings Total:[/bold bright_green] [bold white]{len(findings)}[/bold white]\n\n"
        f"[bold bright_cyan]Entity Type Breakdown:[/bold bright_cyan]\n"
    )

    for entity_type, count in sorted(counts.items()):
        summary_text += f"  • [bright_white]{entity_type:15s}[/bright_white]: [bold bright_green]{count}[/bold bright_green]\n"

    console.print(
        Panel(
            summary_text.strip(),
            title="[bold white]DATA NORMALIZATION SUMMARY[/bold white]",
            border_style="green",
            padding=(0, 2),
        )
    )


def print_correlation_summary(relationships: list):
    """
    Renders a summary panel of correlated relationships grouped by relationship type.
    """
    if not relationships:
        return

    from collections import Counter
    counts = Counter(r.relationship_type for r in relationships)

    summary_text = (
        f"[bold bright_cyan][+] Correlated Relationships Total:[/bold bright_cyan] [bold white]{len(relationships)}[/bold white]\n\n"
        f"[bold bright_cyan]Relationship Type Breakdown:[/bold bright_cyan]\n"
    )

    for rel_type, count in sorted(counts.items()):
        summary_text += f"  • [bright_white]{rel_type:18s}[/bright_white]: [bold bright_cyan]{count}[/bold bright_cyan]\n"

    console.print(
        Panel(
            summary_text.strip(),
            title="[bold white]ENTITY CORRELATION SUMMARY[/bold white]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def print_investigation_summary(
    investigation,
    collector_statuses: dict,
    evidence_store,
    findings: list,
    relationships: list,
):
    """
    Renders the consolidated Executive Terminal Investigation View (MVP 8).
    Displays Collector Statuses, Key Statistics, and High-Level Key Findings.
    """
    from rich.columns import Columns
    from rich.table import Table

    # 1. Collectors Table
    col_table = Table(title="COLLECTORS STATUS", border_style="cyan", header_style="bold bright_cyan")
    col_table.add_column("Collector", style="bright_white")
    col_table.add_column("Status", style="bold bright_green", justify="center")

    for collector_name, status in collector_statuses.items():
        status_style = "bold bright_green" if "COMPLETE" in status or "OK" in status or "SUCCESS" in status else "bold bright_yellow"
        col_table.add_row(collector_name, f"[{status_style}]{status}[/{status_style}]")

    # 2. Statistics Table
    subdomains_count = sum(1 for f in findings if f.entity_type == "SUBDOMAIN")
    tech_count = sum(1 for f in findings if f.entity_type == "TECHNOLOGY")
    dns_infra_count = sum(1 for f in findings if f.entity_type in ("NAME_SERVER", "MAIL_SERVER"))

    stat_table = Table(title="INVESTIGATION STATISTICS", border_style="cyan", header_style="bold bright_cyan")
    stat_table.add_column("Metric", style="bright_white")
    stat_table.add_column("Count", style="bold bright_yellow", justify="right")

    stat_table.add_row("Total Entities", str(len(findings)))
    stat_table.add_row("Subdomains Identified", str(subdomains_count))
    stat_table.add_row("Technologies Detected", str(tech_count))
    stat_table.add_row("Evidence Provenance Items", str(evidence_store.count()))
    stat_table.add_row("Correlated Relationships", str(len(relationships)))

    # 3. Key Findings Box
    key_findings_text = (
        f"[bold white]Key Findings Overview for {investigation.target}:[/bold white]\n\n"
        f"  • [bright_cyan]{subdomains_count}[/bright_cyan] publicly observable subdomains/hostnames\n"
        f"  • [bright_cyan]{tech_count}[/bright_cyan] web technologies detected\n"
        f"  • [bright_cyan]{dns_infra_count}[/bright_cyan] core DNS infrastructure records (NS/MX)\n"
        f"  • [bright_cyan]{len(relationships)}[/bright_cyan] deterministic entity relationships mapped"
    )

    findings_panel = Panel(
        key_findings_text,
        title="[bold white]KEY FINDINGS[/bold white]",
        border_style="bright_magenta",
        padding=(0, 2),
    )

    console.print("\n[bold bright_white on cyan] === EXECUTIVE INVESTIGATION DASHBOARD === [/bold bright_white on cyan]\n")
    console.print(Columns([col_table, stat_table]))
    console.print()
    console.print(findings_panel)


def print_relationship_graph(tree):
    """
    Renders the terminal ASCII/Rich relationship graph.
    """
    console.print("\n[bold bright_cyan]=== TERMINAL RELATIONSHIP GRAPH ===[/bold bright_cyan]\n")
    console.print(tree)
    console.print()
