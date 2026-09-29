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
    banner_text = Text("OSINT INVESTIGATION COPILOT", style="bold white on blue", justify="center")
    subtext = Text("Passive Public-Source Intelligence Collector", style="italic dim white", justify="center")
    
    panel_content = Text()
    panel_content.append(banner_text)
    panel_content.append("\n")
    panel_content.append(subtext)
    
    console.print(Panel(panel_content, border_style="blue", padding=(0, 2)))


def print_investigation_header(investigation: Investigation):
    """
    Displays the initialized investigation details.
    """
    info_text = (
        f"[bold cyan]Investigation ID:[/bold cyan] {investigation.id}\n"
        f"[bold cyan]Target:[/bold cyan]           [bold white]{investigation.target}[/bold white]\n"
        f"[bold cyan]Target Type:[/bold cyan]      {investigation.target_type}\n"
        f"[bold cyan]Started At:[/bold cyan]       {investigation.created_at}\n"
        f"[bold cyan]Status:[/bold cyan]           [green]{investigation.status}[/green]"
    )
    console.print(Panel(info_text, title="[bold]Investigation Initialized[/bold]", border_style="cyan", padding=(0, 2)))


def get_target_domain_interactively() -> str:
    """
    Prompts the user interactively for a domain target with validation.
    """
    while True:
        try:
            raw_input = Prompt.ask("\n[bold yellow]Enter target domain[/bold yellow] (e.g. example.com)").strip()
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

    console.print("\n[bold blue]=== DNS INTELLIGENCE ===[/bold blue]\n")

    if errors.get("domain"):
        console.print(f"[bold red]![/bold red] {errors['domain']}")
        return

    has_records = False
    for rtype, records in findings.items():
        if records:
            has_records = True
            console.print(f"[bold cyan]{rtype} Records[/bold cyan] ({len(records)})")
            for record in records:
                console.print(f"  • [bright_white]{record}[/bright_white]")
            console.print()

    if not has_records:
        console.print("[dim]No DNS records resolved for this target.[/dim]")

    if errors:
        for rtype, err in errors.items():
            console.print(f"[dim yellow]Warning ({rtype}): {err}[/dim yellow]")


def print_evidence_table(evidence_store):
    """
    Renders structured evidence items in a clean Rich table.
    """
    from rich.table import Table

    items = evidence_store.get_all()
    if not items:
        return

    table = Table(title="EVIDENCE PROVENANCE", border_style="cyan", header_style="bold cyan")
    table.add_column("ID", style="bold yellow", width=8)
    table.add_column("Finding", style="white", min_width=20)
    table.add_column("Entity Type", style="green")
    table.add_column("Source", style="magenta")
    table.add_column("Source Reference", style="dim white")

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

    console.print("\n[bold magenta]=== CERTIFICATE INTELLIGENCE ===[/bold magenta]\n")

    if errors.get("crt.sh"):
        console.print(f"[dim yellow]Warning (Certificate Transparency): {errors['crt.sh']}[/dim yellow]")
        if not findings:
            return

    if findings:
        console.print(f"[bold cyan]Publicly Observable Hostnames[/bold cyan] ({len(findings)})")
        # Display max top 15 hostnames cleanly, summarize if larger
        display_limit = 15
        for hostname in findings[:display_limit]:
            console.print(f"  • [bright_white]{hostname}[/bright_white]")
        
        if len(findings) > display_limit:
            console.print(f"  [dim]... and {len(findings) - display_limit} more hostnames (recorded in evidence).[/dim]")

        console.print("\n[italic dim]* Publicly observable hostnames identified through Certificate Transparency.[/italic dim]\n")
    else:
        console.print("[dim]No public Certificate Transparency hostnames observed for this target.[/dim]\n")



