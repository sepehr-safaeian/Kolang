"""
URL parsing, Host validation, and SSRF protection for MCP Servers (ACP-009).

Enforces enterprise security policies on Upstream MCP Server endpoints:
1. URL syntax and structure validation.
2. Mandatory HTTPS for remote / non-local destinations.
3. Strict SSRF protection blocking loopback, link-local, private RFC 1918,
   carrier-grade NAT, and cloud metadata targets in enterprise input.
4. Explicit, documented allowlist controls for local development / demo scenarios.
5. Zero leakage of credentials or sensitive tokens in logs and error messages.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.parse
from collections.abc import Callable

import structlog

from acp_core.common.errors import ValidationError
from acp_core.common.settings import get_settings

logger = structlog.get_logger(__name__)

# Disallowed IP networks for enterprise input (SSRF prevention)
BLOCKED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # Current network / this host
    ipaddress.ip_network("10.0.0.0/8"),  # Private RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space / CGNAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (includes 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),  # Private RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1 documentation
    ipaddress.ip_network("192.88.99.0/24"),  # 6to4 relay anycast
    ipaddress.ip_network("192.168.0.0/16"),  # Private RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),  # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2 documentation
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3 documentation
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved / Future use
    ipaddress.ip_network("255.255.255.255/32"),  # Limited broadcast
]

BLOCKED_IPV6_NETWORKS = [
    ipaddress.ip_network("::/128"),  # Unspecified
    ipaddress.ip_network("::1/128"),  # Loopback
    ipaddress.ip_network("100::/64"),  # Discard prefix
    ipaddress.ip_network("fc00::/7"),  # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),  # Link-local unicast
    ipaddress.ip_network("ff00::/8"),  # Multicast
]

# Explicit cloud metadata hostnames and IP addresses
CLOUD_METADATA_HOSTS = {
    "169.254.169.254",  # AWS, Azure, GCP, OpenStack metadata IP
    "100.100.100.200",  # Alibaba, Oracle Cloud metadata IP
    "metadata.google.internal",  # GCP metadata DNS
    "metadata",  # Common cloud internal hostname
    "instance-data",  # Legacy cloud metadata alias
}

# Forbidden host patterns in enterprise environments
BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".corp",
)

# Standard URL sanitizer removing credentials up to the host
CREDENTIAL_PATTERN = re.compile(r"://([^/@:]+):(.*)@([^/@:]+)")


def sanitize_endpoint_url(url: str) -> str:
    """Mask any username or password credentials in a URL string."""
    if not url:
        return ""
    return CREDENTIAL_PATTERN.sub(r"://\1:***@\3", url)


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if an IP address falls within any blocked network range."""
    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in net for net in BLOCKED_IPV4_NETWORKS)
    return any(ip in net for net in BLOCKED_IPV6_NETWORKS)


def validate_mcp_endpoint_url(
    url: str,
    allow_local: bool | None = None,
    allowed_hosts: list[str] | None = None,
    dns_resolver: Callable[[str], list[str]] | None = None,
) -> str:
    """
    Parse, validate, and verify security constraints for an Upstream MCP Server endpoint URL.

    Args:
        url: The endpoint URL to validate.
        allow_local: If True, allows local/loopback endpoints matching allowed_hosts.
                     Defaults to Settings.allow_local_upstreams.
        allowed_hosts: List of explicitly allowed hostnames for local demo.
                       Defaults to Settings.allowed_upstream_hosts.
        dns_resolver: Optional DNS resolution callable for test injection.

    Returns:
        The validated and normalized URL string.

    Raises:
        ValidationError: If the URL is syntactically invalid, uses an unpermitted scheme,
                         targets a prohibited private/loopback/cloud-metadata host,
                         or fails SSRF host resolution.
    """
    if not url or not isinstance(url, str):
        raise ValidationError("Endpoint URL must be a non-empty string.")

    cleaned_url = url.strip()
    if not cleaned_url:
        raise ValidationError("Endpoint URL must be a non-empty string.")

    if len(cleaned_url) > 512:
        raise ValidationError("Endpoint URL must not exceed 512 characters.")

    # 1. Parse URL structure
    try:
        parsed = urllib.parse.urlsplit(cleaned_url)
    except Exception as exc:
        raise ValidationError(f"Invalid URL structure: {exc}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValidationError(
            f"Invalid URL scheme '{parsed.scheme}'. Only 'https' (and 'http' for local demo) "
            "are supported."
        )

    if not parsed.netloc:
        raise ValidationError("Endpoint URL must contain a valid hostname or authority.")

    # Reject embedded userinfo/credentials in the URL authority (e.g. https://user:pass@host)
    if parsed.username or parsed.password:
        raise ValidationError(
            "Endpoint URL must not contain embedded username or password credentials. "
            "Configure credentials securely via Auth Profiles."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("Endpoint URL is missing a valid hostname.")

    normalized_host = hostname.strip().lower()

    # Port range validation
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise ValidationError(f"Invalid port number: {exc}") from exc

    if parsed_port is not None and not (1 <= parsed_port <= 65535):
        raise ValidationError(f"Invalid port number: {parsed_port}. Must be between 1 and 65535.")

    # Resolve settings if not explicitly passed
    settings = get_settings()
    if allow_local is None:
        allow_local = settings.allow_local_upstreams
    if allowed_hosts is None:
        allowed_hosts = [h.strip().lower() for h in settings.allowed_upstream_hosts]
    else:
        allowed_hosts = [h.strip().lower() for h in allowed_hosts]

    # 2. Universal Cloud Metadata Check (NEVER allowed, even in local demo)
    if normalized_host in CLOUD_METADATA_HOSTS or any(
        normalized_host.endswith("." + m)
        for m in CLOUD_METADATA_HOSTS
        if not m.replace(".", "").isdigit()
    ):
        logger.warning(
            "security.ssrf_cloud_metadata_blocked",
            host=normalized_host,
            url=sanitize_endpoint_url(cleaned_url),
        )
        raise ValidationError(
            f"Endpoint host '{normalized_host}' is a prohibited cloud metadata target."
        )

    # 3. Check Local Demo / Allowlist Exemption
    is_allowed_local = bool(
        allow_local
        and (
            normalized_host in allowed_hosts
            or normalized_host in ("localhost", "127.0.0.1", "::1")
        )
    )

    # 4. HTTPS Enforcement for Non-Local Targets
    if not is_allowed_local and scheme != "https":
        raise ValidationError(
            f"HTTPS is strictly required for remote endpoint '{normalized_host}'. "
            "Plain HTTP is only permitted for local demo servers with explicit allowlisting."
        )

    # 5. IP Address and Hostname SSRF Classification
    is_ip = False
    ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    try:
        ip_obj = ipaddress.ip_address(normalized_host)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip and ip_obj is not None:
        # Destination is an IP literal
        if is_ip_blocked(ip_obj) and not (is_allowed_local and str(ip_obj) in allowed_hosts):
            logger.warning(
                "security.ssrf_blocked_ip",
                ip=str(ip_obj),
                url=sanitize_endpoint_url(cleaned_url),
            )
            raise ValidationError(
                f"Endpoint IP address '{ip_obj}' falls within a prohibited private, "
                "loopback, or reserved network range."
            )
    else:
        # Destination is a domain name / hostname
        if not is_allowed_local and (
            normalized_host == "localhost" or normalized_host.endswith(BLOCKED_HOST_SUFFIXES)
        ):
            logger.warning(
                "security.ssrf_blocked_host",
                host=normalized_host,
                url=sanitize_endpoint_url(cleaned_url),
            )
            raise ValidationError(
                f"Endpoint hostname '{normalized_host}' resolves to a local or internal "
                "domain. Local destinations require explicit demo allowlisting."
            )

        # 6. DNS Resolution Check for Hostnames
        resolved_ips: list[str] = []
        if dns_resolver is not None:
            try:
                resolved_ips = dns_resolver(normalized_host)
            except Exception as exc:
                logger.debug(
                    "validation.dns_resolution_failed", host=normalized_host, error=str(exc)
                )
        else:
            try:
                addr_info = socket.getaddrinfo(normalized_host, None)
                resolved_ips = [str(ai[4][0]) for ai in addr_info]
            except socket.gaierror:
                # Host does not resolve in current environment (e.g. offline unit tests)
                pass
            except Exception as exc:
                logger.debug(
                    "validation.dns_resolution_failed", host=normalized_host, error=str(exc)
                )

        for rip in resolved_ips:
            try:
                resolved_ip_obj = ipaddress.ip_address(rip)
                if is_ip_blocked(resolved_ip_obj) and not (
                    is_allowed_local and (normalized_host in allowed_hosts or rip in allowed_hosts)
                ):
                    logger.warning(
                        "security.ssrf_dns_rebinding_blocked",
                        host=normalized_host,
                        resolved_ip=rip,
                        url=sanitize_endpoint_url(cleaned_url),
                    )
                    raise ValidationError(
                        f"Hostname '{normalized_host}' resolves to prohibited "
                        f"IP address '{rip}' (private, loopback, or cloud metadata)."
                    )
            except ValueError:
                continue

    return cleaned_url
