from typing import Any, Dict, List
import dns.exception
import dns.resolver


class DNSCollector:
    """
    Passive DNS OSINT Collector using dnspython.
    Queries A, AAAA, MX, NS, TXT, and CNAME records.
    Independent of UI/CLI formatting.
    """

    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]

    def __init__(self, timeout: float = 5.0, lifetime: float = 10.0):
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = lifetime

    def collect(self, domain: str) -> Dict[str, Any]:
        """
        Queries DNS records for a validated domain.
        Returns structured dictionary with collector metadata and findings.
        """
        results: Dict[str, List[str]] = {record_type: [] for record_type in self.RECORD_TYPES}
        errors: Dict[str, str] = {}

        for rtype in self.RECORD_TYPES:
            try:
                answers = self.resolver.resolve(domain, rtype)
                for rdata in answers:
                    if rtype == "MX":
                        # Format preference and exchange target
                        results[rtype].append(f"{rdata.preference} {rdata.exchange.to_text().rstrip('.')}")
                    elif rtype in ("NS", "CNAME"):
                        results[rtype].append(rdata.target.to_text().rstrip('.'))
                    elif rtype == "TXT":
                        # Join quote blocks in TXT records
                        txt_val = "".join([b.decode("utf-8", errors="replace") for b in rdata.strings])
                        results[rtype].append(txt_val)
                    else:
                        results[rtype].append(rdata.to_text())
            except dns.resolver.NoAnswer:
                # Normal condition when domain lacks specific record type
                pass
            except dns.resolver.NXDOMAIN:
                errors["domain"] = f"Domain '{domain}' does not exist (NXDOMAIN)."
                break
            except dns.resolver.Timeout:
                errors[rtype] = f"DNS query for {rtype} timed out."
            except dns.exception.DNSException as e:
                errors[rtype] = f"DNS resolution error: {str(e)}"
            except Exception as e:
                errors[rtype] = f"Unexpected error: {str(e)}"

        return {
            "collector": "dns",
            "target": domain,
            "findings": results,
            "errors": errors,
        }
