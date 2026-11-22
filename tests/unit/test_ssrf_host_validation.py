"""
Unit tests for URL Host Validation and SSRF Protection (ACP-009).

Verifies:
- Structural URL validation (schemes, authority, credentials, ports).
- Mandatory HTTPS for remote / non-local targets.
- SSRF prevention blocking loopback, link-local, private networks, and CGNAT.
- Cloud metadata IP and hostname protection (169.254.169.254, metadata.google.internal).
- DNS rebinding prevention via resolved IP checks.
- Local demo allowlisting controls (allow_local and allowed_hosts).
- Safe credential masking in URL sanitization.
"""

from __future__ import annotations

import ipaddress

import pytest

from acp_core.common.errors import ValidationError
from acp_core.registry.validation import (
    is_ip_blocked,
    sanitize_endpoint_url,
    validate_mcp_endpoint_url,
)

# ── URL Structural & Syntax Validation ────────────────────────────────────────


@pytest.mark.parametrize(
    ("invalid_url", "match_msg"),
    [
        ("", "non-empty string"),
        ("   ", "non-empty string"),
        ("ftp://files.example.com/mcp", "Only 'https'"),
        ("file:///etc/passwd", "Only 'https'"),
        ("gopher://evil.com/mcp", "Only 'https'"),
        ("data:text/plain;base64,SGVsbG8=", "Only 'https'"),
        ("javascript:alert(1)", "Only 'https'"),
        ("https://", "valid hostname or authority"),
        ("https://:8080/mcp", "missing a valid hostname"),
        ("https://api.example.com:0/mcp", "Invalid port number"),
        ("https://api.example.com:70000/mcp", "Invalid port number"),
        ("https://api.example.com:-1/mcp", "Invalid port number"),
    ],
)
def test_url_syntax_and_scheme_validation_failures(invalid_url: str, match_msg: str) -> None:
    """Verify malformed URLs and unsupported schemes are rejected."""
    with pytest.raises(ValidationError, match=match_msg):
        validate_mcp_endpoint_url(invalid_url)


def test_url_rejects_embedded_credentials() -> None:
    """Verify endpoint URLs with embedded basic auth credentials are strictly rejected."""
    with pytest.raises(ValidationError, match="embedded username or password"):
        validate_mcp_endpoint_url("https://admin:supersecret@api.example.com/mcp")


def test_url_length_limit() -> None:
    """Verify endpoint URLs exceeding 512 characters are rejected."""
    long_url = "https://api.example.com/" + "a" * 500
    with pytest.raises(ValidationError, match="must not exceed 512 characters"):
        validate_mcp_endpoint_url(long_url)


# ── HTTPS Enforcement for Non-Local Targets ───────────────────────────────────


def test_remote_http_rejected() -> None:
    """Verify plain HTTP is rejected for remote endpoints."""
    with pytest.raises(ValidationError, match="HTTPS is strictly required for remote endpoint"):
        validate_mcp_endpoint_url("http://api.remote-mcp.org/mcp", allow_local=False)


def test_remote_https_accepted() -> None:
    """Verify valid public HTTPS endpoints are accepted."""
    url = "https://api.github.com/mcp"
    validated = validate_mcp_endpoint_url(url, allow_local=False)
    assert validated == url


# ── SSRF / Host Validation for Prohibited IP Ranges ──────────────────────────


@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",  # IPv4 Loopback
        "127.0.1.1",  # IPv4 Loopback subnet
        "10.0.0.1",  # Private RFC 1918 (10/8)
        "10.254.254.1",
        "172.16.0.1",  # Private RFC 1918 (172.16/12)
        "172.31.255.254",
        "192.168.1.1",  # Private RFC 1918 (192.168/16)
        "192.168.100.50",
        "169.254.1.1",  # Link-local (169.254/16)
        "169.254.169.254",  # Cloud metadata IP
        "100.64.0.1",  # CGNAT (100.64/10)
        "100.127.255.254",
        "0.0.0.0",  # noqa: S104 # Current network
        "224.0.0.1",  # Multicast
        "::1",  # IPv6 Loopback
        "fe80::1",  # IPv6 Link-local
        "fc00::1",  # IPv6 ULA
        "fd12:3456::1",  # IPv6 ULA
    ],
)
def test_blocked_ip_ranges_rejected(blocked_ip: str) -> None:
    """Verify that private, loopback, and link-local IP addresses are blocked."""
    ip_obj = ipaddress.ip_address(blocked_ip)
    assert is_ip_blocked(ip_obj) is True

    # Check URL validation rejection
    url = f"https://{blocked_ip}/mcp" if ":" not in blocked_ip else f"https://[{blocked_ip}]/mcp"
    with pytest.raises(ValidationError):
        validate_mcp_endpoint_url(url, allow_local=False)


# ── Cloud Metadata Protection ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cloud_target",
    [
        "http://169.254.169.254/latest/meta-data/",
        "https://169.254.169.254/computeMetadata/v1",
        "http://metadata.google.internal/computeMetadata/v1",
        "https://metadata.google.internal/mcp",
        "http://metadata/mcp",
        "http://100.100.100.200/latest/meta-data",
    ],
)
def test_cloud_metadata_always_blocked(cloud_target: str) -> None:
    """Verify cloud metadata IPs and hostnames are rejected even if allow_local is True."""
    # Test with allow_local=False
    with pytest.raises(ValidationError, match="prohibited cloud metadata target"):
        validate_mcp_endpoint_url(cloud_target, allow_local=False)

    # Test with allow_local=True (still blocked!)
    with pytest.raises(ValidationError, match="prohibited cloud metadata target"):
        validate_mcp_endpoint_url(
            cloud_target,
            allow_local=True,
            allowed_hosts=[
                "localhost",
                "127.0.0.1",
                "metadata.google.internal",
                "169.254.169.254",
            ],
        )


# ── DNS Rebinding Prevention ─────────────────────────────────────────────────


def test_dns_rebinding_to_private_ip_blocked() -> None:
    """Verify that hostnames resolving to private/loopback IPs are blocked."""

    # Mock DNS resolver returning a private loopback address
    def mock_evil_resolver(host: str) -> list[str]:
        return ["127.0.0.1"]

    with pytest.raises(ValidationError, match=r"resolves to prohibited IP address '127\.0\.0\.1'"):
        validate_mcp_endpoint_url(
            "https://evil-rebinding-domain.com/mcp",
            allow_local=False,
            dns_resolver=mock_evil_resolver,
        )


def test_dns_rebinding_to_metadata_ip_blocked() -> None:
    """Verify that hostnames resolving to cloud metadata IP are blocked."""

    def mock_metadata_resolver(host: str) -> list[str]:
        return ["169.254.169.254"]

    with pytest.raises(
        ValidationError, match=r"resolves to prohibited IP address '169\.254\.169\.254'"
    ):
        validate_mcp_endpoint_url(
            "https://sneaky-metadata-proxy.com/mcp",
            allow_local=False,
            dns_resolver=mock_metadata_resolver,
        )


def test_dns_resolution_to_public_ip_accepted() -> None:
    """Verify that hostnames resolving to legitimate public IPs are accepted."""

    def mock_public_resolver(host: str) -> list[str]:
        return ["93.184.216.34"]  # example.com public IP

    url = "https://trusted-mcp.org/mcp"
    validated = validate_mcp_endpoint_url(
        url,
        allow_local=False,
        dns_resolver=mock_public_resolver,
    )
    assert validated == url


# ── Local Demo Allowlist Behavior ─────────────────────────────────────────────


def test_local_demo_disabled_by_default() -> None:
    """Verify localhost is rejected when allow_local is False."""
    with pytest.raises(ValidationError, match="HTTPS is strictly required"):
        validate_mcp_endpoint_url("http://localhost:8080/mcp", allow_local=False)

    with pytest.raises(ValidationError, match="resolves to a local or internal domain"):
        validate_mcp_endpoint_url("https://localhost:8080/mcp", allow_local=False)


def test_local_demo_allowed_with_explicit_configuration() -> None:
    """Verify localhost and 127.0.0.1 with plain HTTP are accepted when allow_local is True."""
    # Localhost
    url1 = "http://localhost:8080/mcp"
    val1 = validate_mcp_endpoint_url(
        url1,
        allow_local=True,
        allowed_hosts=["localhost", "127.0.0.1"],
    )
    assert val1 == url1

    # 127.0.0.1
    url2 = "http://127.0.0.1:8080/mcp"
    val2 = validate_mcp_endpoint_url(
        url2,
        allow_local=True,
        allowed_hosts=["localhost", "127.0.0.1"],
    )
    assert val2 == url2


def test_local_demo_rejects_unlisted_local_host() -> None:
    """Verify local targets outside explicit allowlist are rejected even with allow_local=True."""
    with pytest.raises(ValidationError):
        validate_mcp_endpoint_url(
            "http://192.168.1.50:8080/mcp",
            allow_local=True,
            allowed_hosts=["localhost", "127.0.0.1"],  # 192.168.1.50 is not in allowlist
        )


# ── Sanitization and Credential Redaction ─────────────────────────────────────


def test_sanitize_endpoint_url_redacts_credentials() -> None:
    """Verify sanitize_endpoint_url redacts embedded user:pass credentials."""
    raw = "https://app_user:s3cr3tP@ssw0rd!@upstream.example.com:8443/mcp"
    sanitized = sanitize_endpoint_url(raw)
    assert "s3cr3tP@ssw0rd!" not in sanitized
    assert sanitized == "https://app_user:***@upstream.example.com:8443/mcp"


def test_sanitize_endpoint_url_leaves_clean_url_intact() -> None:
    """Verify clean URLs without credentials are not modified."""
    clean = "https://api.github.com/mcp"
    assert sanitize_endpoint_url(clean) == clean
    assert sanitize_endpoint_url("") == ""
