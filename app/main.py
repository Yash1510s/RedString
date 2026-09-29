import sys
import argparse
from app.cli.interface import (
    console,
    print_banner,
    print_investigation_header,
    get_target_domain_interactively,
    print_error,
)
from app.core.models import Investigation
from app.core.validation import validate_domain


def run_app():
    """
    Main entrypoint function for OSINT Copilot MVP 1 CLI.
    """
    print_banner()

    parser = argparse.ArgumentParser(
        description="OSINT Investigation Copilot - Passive Domain Intelligence Tool",
        add_help=False,
    )
    parser.add_argument("domain", nargs="?", help="Target domain name (e.g., example.com)")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message")

    args, _ = parser.parse_known_args()

    if args.help:
        console.print("[bold cyan]Usage:[/bold cyan]")
        console.print("  python run.py [domain]")
        console.print("  python run.py               (interactive mode)\n")
        return

    target_domain = None

    if args.domain:
        is_valid, result = validate_domain(args.domain)
        if not is_valid:
            print_error(result)
            sys.exit(1)
        target_domain = result
    else:
        target_domain = get_target_domain_interactively()

    # Create investigation instance
    investigation = Investigation(target=target_domain)

    # Render initial header
    print_investigation_header(investigation)

    console.print("\n[dim]MVP 1 Application Shell initialized successfully.[/dim]")
    console.print("[dim]Collectors (DNS, Certificate Transparency, Technologies) will be added in subsequent phases.[/dim]\n")


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Investigation cancelled by user.[/bold yellow]")
        sys.exit(0)
