import re
from typing import Tuple

# Standard regex for hostname validation
DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# IPv4 regex
IPV4_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


def validate_domain(input_string: str) -> Tuple[bool, str]:
    """
    Validates that input is a valid public domain name.
    Returns (is_valid, normalized_domain_or_error_message).
    """
    if not input_string:
        return False, "Domain input cannot be empty."

    cleaned = input_string.strip().lower()

    # Reject protocol prefixes
    if "://" in cleaned:
        return False, "Target must be a domain name only (do not include http:// or https://)."

    # Reject userinfo, paths, ports, or query strings
    if "@" in cleaned:
        return False, "Target must not contain user credentials (@ symbol)."
    if "/" in cleaned or "\\" in cleaned:
        return False, "Target must not contain URL paths."
    if ":" in cleaned:
        return False, "Target must not specify port numbers."
    if "?" in cleaned or "#" in cleaned:
        return False, "Target must not contain query parameters or fragments."

    # Reject IPv4 addresses
    if IPV4_REGEX.match(cleaned):
        return False, "Target must be a domain name, not an IP address."

    # Reject reserved / localhost names
    if cleaned in ("localhost", "local", "invalid") or cleaned.endswith(".local") or cleaned.endswith(".localhost"):
        return False, "Target must be a public domain name, not a local or reserved hostname."

    # Strip trailing dot if present for standard comparison
    if cleaned.endswith("."):
        cleaned = cleaned[:-1]

    # Check against domain regex
    if not DOMAIN_REGEX.match(cleaned):
        return False, f"'{cleaned}' is not a valid public domain name (e.g. example.com)."

    return True, cleaned
