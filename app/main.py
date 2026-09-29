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

    # Execute MVP 2: DNS Collector & MVP 4: Certificate Transparency Collector
    from app.collectors.dns import DNSCollector
    from app.collectors.certificates import CertificateCollector
    from app.core.evidence import EvidenceStore
    from app.cli.interface import (
        print_dns_findings,
        print_certificate_findings,
        print_evidence_table,
    )

    evidence_store = EvidenceStore()

    # Query DNS
    with console.status("[bold green]Collecting DNS records...[/bold green]", spinner="dots"):
        dns_collector = DNSCollector()
        dns_results = dns_collector.collect(target_domain)

    print_dns_findings(dns_results)
    evidence_store.ingest_dns_results(dns_results)

    # Query Certificate Transparency
    with console.status("[bold magenta]Querying Certificate Transparency logs...[/bold magenta]", spinner="dots"):
        cert_collector = CertificateCollector()
        cert_results = cert_collector.collect(target_domain)

    print_certificate_findings(cert_results)
    evidence_store.ingest_certificate_results(cert_results)

    # Display consolidated Evidence table
    print_evidence_table(evidence_store)





if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Investigation cancelled by user.[/bold yellow]")
        sys.exit(0)
