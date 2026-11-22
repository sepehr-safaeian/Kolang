"""
Validation, bounds enforcement, and fingerprinting for MCP Tools (ACP-010).

Enforces security boundaries and data hygiene on tool catalog definitions:
1. Input schemas and descriptions are treated as UNTRUSTED upstream data.
2. JSON schema is strictly an input contract, not proof of secure execution behavior.
3. Oversized payloads, deeply nested schemas, or invalid types are rejected.
4. Deterministic SHA-256 fingerprinting for change detection and catalog hashing.
5. Independent multi-dimensional risk labels instead of ambiguous risk scores.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Any

from acp_core.common.errors import ValidationError

# Tool name pattern: 1-100 alphanumeric, underscore, dot, colon, or hyphen
TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.:-]{1,100}$")

# Risk label pattern: lowercase alphanumeric, underscore, colon, hyphen
RISK_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_:-]{0,49}$")

# Security bounds
MAX_TOOL_NAME_LENGTH = 100
MAX_TOOL_TITLE_LENGTH = 255
MAX_TOOL_DESCRIPTION_LENGTH = 4096
MAX_INPUT_SCHEMA_BYTES = 65536  # 64 KB
MAX_SCHEMA_DEPTH = 10
MAX_RISK_LABELS_COUNT = 50
MAX_ANNOTATIONS_BYTES = 16384  # 16 KB


def validate_tool_name(name: str) -> str:
    """
    Validate tool identifier format and length.

    Args:
        name: Proposed tool name.

    Returns:
        Cleaned tool name string.

    Raises:
        ValidationError: If tool name is empty, too long, or contains disallowed characters.
    """
    cleaned = name.strip()
    if not cleaned:
        raise ValidationError("Tool name cannot be empty or whitespace only.")
    if len(cleaned) > MAX_TOOL_NAME_LENGTH:
        raise ValidationError(
            f"Tool name exceeds maximum length of {MAX_TOOL_NAME_LENGTH} characters."
        )
    if not TOOL_NAME_PATTERN.match(cleaned):
        raise ValidationError(
            f"Invalid tool name format: '{name}'. Must be 1-100 characters consisting of "
            "alphanumeric characters, underscores, hyphens, dots, or colons."
        )
    return cleaned


def validate_tool_title(title: str | None) -> str | None:
    """
    Validate optional human-readable display title.

    Args:
        title: Optional title.

    Returns:
        Cleaned title or None.

    Raises:
        ValidationError: If title exceeds maximum permitted length.
    """
    if title is None:
        return None
    cleaned = title.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_TOOL_TITLE_LENGTH:
        raise ValidationError(
            f"Tool title exceeds maximum length of {MAX_TOOL_TITLE_LENGTH} characters."
        )
    return cleaned


def validate_tool_description(description: str) -> str:
    """
    Sanitize and bound untrusted tool description text.

    Upstream MCP servers may provide arbitrary, untrusted descriptions.
    Enforces maximum length limits to prevent resource exhaustion or storage attacks.

    Args:
        description: Raw description string.

    Returns:
        Cleaned description string within safe bounds.

    Raises:
        ValidationError: If description exceeds MAX_TOOL_DESCRIPTION_LENGTH.
    """
    cleaned = description.strip()
    if len(cleaned) > MAX_TOOL_DESCRIPTION_LENGTH:
        raise ValidationError(
            f"Tool description exceeds maximum allowed length of "
            f"{MAX_TOOL_DESCRIPTION_LENGTH} characters (received {len(cleaned)})."
        )
    return cleaned


def _calculate_dict_depth(obj: Any, current_depth: int = 1) -> int:
    """Recursively calculate the maximum nesting depth of a dictionary or list structure."""
    if current_depth > MAX_SCHEMA_DEPTH:
        return current_depth
    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(_calculate_dict_depth(v, current_depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current_depth
        return max(_calculate_dict_depth(item, current_depth + 1) for item in obj)
    return current_depth


def validate_tool_input_schema(
    schema: Any,
    max_bytes: int = MAX_INPUT_SCHEMA_BYTES,
    max_depth: int = MAX_SCHEMA_DEPTH,
) -> dict[str, Any]:
    """
    Validate and bound an untrusted MCP tool input schema.

    Enforces:
    1. Schema must be a valid JSON dictionary structure.
    2. Serialized JSON payload must not exceed `max_bytes` (default 64 KB).
    3. Nesting depth must not exceed `max_depth` (default 10) to prevent ReDoS attacks.
    4. Schema must be serializable without error.

    Args:
        schema: Raw input schema from MCP tools/list discovery.
        max_bytes: Maximum allowed serialized byte size.
        max_depth: Maximum allowed nesting level.

    Returns:
        Validated schema dictionary.

    Raises:
        ValidationError: If schema is invalid, non-serializable, or exceeds safety thresholds.
    """
    if not isinstance(schema, dict):
        raise ValidationError(
            f"Tool input_schema must be a dictionary/JSON object, got {type(schema).__name__}."
        )

    # Check serialization and byte size
    try:
        serialized = json.dumps(schema, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError) as err:
        raise ValidationError(f"Tool input_schema is not serializable JSON: {err}") from err

    byte_len = len(serialized.encode("utf-8"))
    if byte_len > max_bytes:
        raise ValidationError(
            f"Tool input_schema size ({byte_len} bytes) exceeds maximum permitted limit "
            f"of {max_bytes} bytes."
        )

    # Check recursion depth
    depth = _calculate_dict_depth(schema)
    if depth > max_depth:
        msg = f"Tool input_schema nesting depth ({depth}) exceeds maximum limit of {max_depth}."
        raise ValidationError(msg)

    return schema


def validate_tool_annotations(
    annotations: Any,
    max_bytes: int = MAX_ANNOTATIONS_BYTES,
) -> dict[str, Any] | None:
    """
    Validate optional tool annotations provided by the protocol/SDK.

    Args:
        annotations: Optional dictionary of annotations (e.g. read_only_hint, audience).
        max_bytes: Maximum allowed byte size.

    Returns:
        Validated annotations dictionary or None.

    Raises:
        ValidationError: If annotations is not a dictionary or exceeds max byte size.
    """
    if annotations is None:
        return None
    if not isinstance(annotations, dict):
        raise ValidationError(
            f"Tool annotations must be a dictionary, got {type(annotations).__name__}."
        )

    try:
        serialized = json.dumps(annotations, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError) as err:
        raise ValidationError(f"Tool annotations is not serializable JSON: {err}") from err

    byte_len = len(serialized.encode("utf-8"))
    if byte_len > max_bytes:
        raise ValidationError(
            f"Tool annotations size ({byte_len} bytes) exceeds maximum limit of {max_bytes} bytes."
        )

    return annotations


def validate_risk_labels(labels: Any) -> list[str]:
    """
    Validate and normalize independent risk labels.

    Replaces ambiguous single risk scores with explicit, discrete security tags
    (e.g., 'filesystem:read', 'network:outbound', 'system:exec', 'credentials:read').

    Args:
        labels: Iterable of label strings.

    Returns:
        Sorted, deduplicated list of lowercase normalized label strings.

    Raises:
        ValidationError: If labels contains invalid formats or exceeds max count.
    """
    if labels is None:
        return []
    if not isinstance(labels, (list, tuple, set)):
        raise ValidationError(
            f"Risk labels must be a list or set of strings, got {type(labels).__name__}."
        )

    normalized: set[str] = set()
    for raw in labels:
        if not isinstance(raw, str):
            raise ValidationError(f"Risk label must be a string, got {type(raw).__name__}.")
        cleaned = raw.strip().lower()
        if not cleaned:
            continue
        if not RISK_LABEL_PATTERN.match(cleaned):
            raise ValidationError(
                f"Invalid risk label format: '{raw}'. Must be 1-50 characters consisting of "
                "lowercase letters, numbers, underscores, colons, or hyphens."
            )
        normalized.add(cleaned)

    if len(normalized) > MAX_RISK_LABELS_COUNT:
        raise ValidationError(
            f"Risk labels count ({len(normalized)}) exceeds maximum of {MAX_RISK_LABELS_COUNT}."
        )

    return sorted(normalized)


def compute_tool_fingerprint(
    name: str,
    input_schema: dict[str, Any],
    description: str | None = "",
    title: str | None = None,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint for a tool definition.

    Canonicalizes the tool name, title, description, and input schema to ensure
    identical definitions produce identical hash representations for drift detection.

    Args:
        name: Tool name.
        input_schema: Validated tool input schema.
        description: Untrusted description.
        title: Optional tool title.

    Returns:
        64-character hexadecimal SHA-256 string.
    """
    canonical_payload = {
        "name": (name or "").strip(),
        "title": (title or "").strip(),
        "description": (description or "").strip(),
        "input_schema": input_schema,
    }
    canonical_json = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_catalog_hash(tools: Sequence[dict[str, Any]]) -> str:
    """
    Compute a deterministic SHA-256 hash for an entire discovered tool catalog snapshot.

    Sorts individual tools by name and computes a cumulative fingerprint to enable
    instant catalog drift detection between discovery runs.

    Args:
        tools: Sequence of tool definition dictionaries.

    Returns:
        64-character hexadecimal SHA-256 string.
    """
    fingerprints: list[str] = []
    for tool in tools:
        t_name = str(tool.get("name", ""))
        t_schema = tool.get("input_schema", {})
        t_desc = str(tool.get("description", ""))
        t_title = tool.get("title")
        fp = compute_tool_fingerprint(
            name=t_name,
            input_schema=t_schema if isinstance(t_schema, dict) else {},
            description=t_desc,
            title=t_title if isinstance(t_title, str) else None,
        )
        fingerprints.append(f"{t_name}:{fp}")

    fingerprints.sort()
    catalog_repr = "\n".join(fingerprints)
    return hashlib.sha256(catalog_repr.encode("utf-8")).hexdigest()
