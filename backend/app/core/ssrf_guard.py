"""SSRF Protection and Target Domain Validation per Spec Rules S2 & S3."""

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx

MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB response limit
DEFAULT_TIMEOUT_SECONDS = 10.0
ALLOWED_PORTS = {80, 443}
ALLOWED_SCHEMES = {"http", "https"}

DISALLOWED_TLDS = {
    "local",
    "lan",
    "internal",
    "home",
    "corp",
    "test",
    "example",
    "invalid",
    "onion",
    "arpa",
    "localhost",
}

# RFC 1123 compliant hostname regex
DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


class SSRFSecurityViolation(Exception):
    """Raised when an outbound network request violates SSRF security boundaries."""

    pass


class InvalidTargetError(ValueError):
    """Raised when an entered investigation target is invalid."""

    pass


def validate_target_domain(target: str) -> str:
    """Validate target domain string per Spec Rule S3.

    - Must be a valid public hostname.
    - Rejects IP literals, localhost, credentials, paths, ports, or schemes.
    """
    if not target or not isinstance(target, str):
        raise InvalidTargetError("Target domain cannot be empty.")

    clean = target.strip()

    # Reject URLs / schemes
    if clean.startswith(("http://", "https://", "ftp://", "file://")):
        raise InvalidTargetError("Target must be a domain name, not a URL with scheme.")

    # Reject credentials, paths, query strings, fragments, or ports
    disallowed_chars = {"@", "/", "\\", ":", "?", "#", "[", "]"}
    if any(char in clean for char in disallowed_chars):
        raise InvalidTargetError("Target contains invalid characters (credentials, paths, ports).")

    # Reject IP literals (IPv4 and IPv6)
    try:
        ipaddress.ip_address(clean)
        raise InvalidTargetError("IP literals are not permitted as investigation targets.")
    except ValueError:
        # Not an IP literal, which is expected
        pass

    # Normalize Punycode / IDNA
    try:
        clean = clean.encode("idna").decode("ascii").lower()
    except Exception as exc:
        msg = "Target contains invalid international domain characters."
        raise InvalidTargetError(msg) from exc

    if clean.endswith("."):
        clean = clean[:-1]

    if clean == "localhost":
        raise InvalidTargetError("Target 'localhost' is not permitted.")

    parts = clean.split(".")
    if len(parts) < 2:
        raise InvalidTargetError("Target must have a valid public top-level domain (TLD).")

    tld = parts[-1].lower()
    if tld in DISALLOWED_TLDS:
        raise InvalidTargetError(f"Internal or reserved TLD '.{tld}' is not permitted.")

    if not DOMAIN_REGEX.match(clean):
        raise InvalidTargetError(f"Target '{clean}' is not a syntactically valid domain name.")

    return clean


def is_ip_allowed(ip_val: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check whether an IP address is a safe, routable public address.

    Rejects:
    - Loopback (127.0.0.0/8, ::1)
    - Private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7)
    - Link-local (169.254.0.0/16, fe80::/10)
    - Multicast & Reserved
    - Cloud metadata (169.254.169.254)
    - Carrier-grade NAT (100.64.0.0/10)
    """
    if isinstance(ip_val, str):
        try:
            ip = ipaddress.ip_address(ip_val.strip())
        except ValueError:
            return False
    else:
        ip = ip_val

    # Reject loopback, private, link-local, multicast, reserved, unspecified
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return False

    # Explicit cloud metadata check (AWS/GCP/Azure IMDS)
    if str(ip) == "169.254.169.254":
        return False

    # Carrier-grade NAT check for IPv4 (100.64.0.0/10)
    if isinstance(ip, ipaddress.IPv4Address):
        cgnat = ipaddress.IPv4Network("100.64.0.0/10")
        if ip in cgnat:
            return False

    return True


async def resolve_and_validate_hostname(hostname: str) -> list[str]:
    """Resolve a hostname via DNS and ensure all resolved IP addresses are safe.

    Raises SSRFSecurityViolation if any resolved IP address is in a prohibited range.
    """
    clean_host = hostname.strip().lower()
    if clean_host == "localhost" or clean_host.endswith(".localhost"):
        raise SSRFSecurityViolation("Requests to localhost are blocked by SSRF guard.")

    loop = asyncio.get_running_loop()
    try:
        addr_info = await loop.getaddrinfo(
            clean_host,
            None,
            family=0,
            type=socket.SOCK_STREAM,
        )
    except Exception as exc:
        raise SSRFSecurityViolation(f"Unable to resolve host '{clean_host}': {exc}") from exc

    if not addr_info:
        raise SSRFSecurityViolation(f"Host '{clean_host}' resolved to no IP addresses.")

    resolved_ips: list[str] = []
    for info in addr_info:
        sockaddr = info[4]
        ip_str = str(sockaddr[0])
        if not is_ip_allowed(ip_str):
            raise SSRFSecurityViolation(
                f"SSRF Guard blocked host '{clean_host}': resolved to prohibited IP '{ip_str}'."
            )
        resolved_ips.append(ip_str)

    return list(dict.fromkeys(resolved_ips))


def validate_outbound_url(url: str) -> tuple[str, str, int]:
    """Validate URL scheme, port, and structure. Returns (scheme, hostname, port)."""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme not in ALLOWED_SCHEMES:
        raise SSRFSecurityViolation(f"Scheme '{scheme}' is prohibited. Only http/https allowed.")

    if parsed.username or parsed.password:
        raise SSRFSecurityViolation("URLs containing embedded credentials are prohibited.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityViolation(f"Invalid URL '{url}': missing hostname.")

    port = parsed.port or (443 if scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise SSRFSecurityViolation(
            f"Port '{port}' is prohibited. Only ports 80 and 443 are allowed."
        )

    return scheme, hostname, port


class SafeHttpClient:
    """Async HTTP client enforcing pre-flight DNS, redirect validation, and size capping."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """Perform a safe GET request.

        Returns (status_code, response_headers, response_bytes).
        Enforces:
        - Port 80/443 only
        - Pre-request IP resolution check
        - Max 3 redirects, each independently validated
        - 2 MB response size cap
        """
        current_url = url
        redirect_count = 0
        req_headers = {"User-Agent": "RedString-OSINT-Copilot/1.0"}
        if headers:
            req_headers.update(headers)

        while True:
            scheme, hostname, port = validate_outbound_url(current_url)

            # Pre-flight DNS validation
            await resolve_and_validate_hostname(hostname)

            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=False,
                verify=True,
            ) as client:
                try:
                    response = await client.get(current_url, headers=req_headers)
                except Exception as exc:
                    msg = f"HTTP request to '{current_url}' failed: {exc}"
                    raise SSRFSecurityViolation(msg) from exc

            # Handle redirects manually to re-validate each hop
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location:
                    break

                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise SSRFSecurityViolation(
                        f"Exceeded maximum allowed redirects ({MAX_REDIRECTS})."
                    )

                # Resolve relative redirects against current URL
                current_url = str(httpx.URL(current_url).join(location))
                continue

            # Read and cap response body to 2 MB
            content = response.content
            if len(content) > MAX_RESPONSE_BYTES:
                content = content[:MAX_RESPONSE_BYTES]

            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            return response.status_code, resp_headers, content

        raise SSRFSecurityViolation("Request loop terminated without response.")
