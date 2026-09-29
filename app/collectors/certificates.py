from typing import Any, Dict, List, Set, Tuple
import time
import httpx


class CertificateCollector:
    """
    Passive Certificate Transparency OSINT Collector using public crt.sh API.
    Queries public Certificate Transparency logs to find observable hostnames/SANs.
    Implements fallback strategies to handle crt.sh server load/502 Bad Gateway errors.
    """

    CRT_SH_URL = "https://crt.sh/"

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _query_crt_sh(self, client: httpx.Client, query_param: str) -> Tuple[List[Dict[str, Any]], int]:
        params = {"q": query_param, "output": "json"}
        response = client.get(self.CRT_SH_URL, params=params)
        if response.status_code == 200:
            return response.json(), 200
        return [], response.status_code

    def collect(self, domain: str) -> Dict[str, Any]:
        """
        Queries crt.sh for public certificate records for the target domain.
        Returns structured dictionary with deduplicated hostnames and errors if any.
        """
        hostnames: Set[str] = set()
        errors: Dict[str, str] = {}

        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                data = []
                status_code = 0
                
                # Attempt 1: Wildcard query (%.domain)
                try:
                    data, status_code = self._query_crt_sh(client, f"%.{domain}")
                except (httpx.TimeoutException, httpx.RequestError):
                    raise
                except Exception:
                    status_code = 0

                # Attempt 2: If 502/error on wildcard, fallback to direct domain query (domain)
                if status_code != 200 or not data:
                    try:
                        time.sleep(0.5)
                        data, status_code = self._query_crt_sh(client, domain)
                    except (httpx.TimeoutException, httpx.RequestError):
                        raise
                    except Exception:
                        pass

                if status_code == 200 and data:
                    for entry in data:
                        name_value = entry.get("name_value", "")
                        for line in name_value.split("\n"):
                            cleaned = line.strip().lower()
                            if cleaned.startswith("*."):
                                cleaned = cleaned[2:]
                            if cleaned and (cleaned == domain or cleaned.endswith(f".{domain}")):
                                hostnames.add(cleaned)
                elif status_code != 200:
                    if status_code == 502:
                        errors["crt.sh"] = "crt.sh PostgreSQL backend returned 502 Bad Gateway (server database overload)."
                    else:
                        errors["crt.sh"] = f"crt.sh API returned HTTP status {status_code}."

        except httpx.TimeoutException:
            errors["crt.sh"] = "Certificate Transparency query to crt.sh timed out."
        except httpx.RequestError as e:
            errors["crt.sh"] = f"Network error querying crt.sh: {str(e)}"
        except Exception as e:
            errors["crt.sh"] = f"Unexpected error during CT collection: {str(e)}"

        sorted_hostnames = sorted(list(hostnames))

        return {
            "collector": "certificate_transparency",
            "target": domain,
            "findings": sorted_hostnames,
            "errors": errors,
        }
