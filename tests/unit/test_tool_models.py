"""
Unit tests for Tool and Tool Snapshot domain models and validation (ACP-010).

Verifies:
- Tool and ToolSnapshot Pydantic schema validation, defaults, and serialization.
- Untrusted tool description bounding and sanitization.
- Untrusted input schema validation (rejection of non-dicts, size bloat, and deep recursion).
- Multi-dimensional risk labels validation (independent labels, format, deduplication).
- Deterministic SHA-256 fingerprinting and catalog hashing.
- Classification status lifecycle values.
- ORM model instantiation and representation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from acp_core.common.errors import ValidationError as AcpValidationError
from acp_core.registry.tool_models import (
    Tool,
    ToolClassificationStatus,
    ToolCreate,
    ToolSnapshot,
    ToolSnapshotCreate,
    ToolSnapshotRead,
)
from acp_core.registry.tool_validation import (
    MAX_TOOL_DESCRIPTION_LENGTH,
    compute_catalog_hash,
    compute_tool_fingerprint,
    validate_risk_labels,
    validate_tool_description,
    validate_tool_input_schema,
    validate_tool_name,
    validate_tool_title,
)


def test_tool_classification_status_enum_values() -> None:
    """Verify supported tool classification status values."""
    assert ToolClassificationStatus.UNCLASSIFIED.value == "unclassified"
    assert ToolClassificationStatus.SAFE.value == "safe"
    assert ToolClassificationStatus.SENSITIVE.value == "sensitive"
    assert ToolClassificationStatus.RESTRICTED.value == "restricted"
    assert ToolClassificationStatus.FORBIDDEN.value == "forbidden"


def test_tool_create_valid_defaults() -> None:
    """Verify valid ToolCreate payload with default fields."""
    workspace_id = uuid.uuid4()
    server_id = uuid.uuid4()
    tool = ToolCreate(
        workspace_id=workspace_id,
        server_id=server_id,
        name="execute_query",
        description="Run a read-only SQL query against the warehouse.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    )
    assert tool.name == "execute_query"
    assert tool.title is None
    assert tool.classification_status == ToolClassificationStatus.UNCLASSIFIED
    assert tool.risk_labels == []
    assert tool.is_enabled is True
    assert tool.annotations is None

    # Verify auto-computed fingerprint
    fp = tool.resolve_fingerprint()
    assert isinstance(fp, str)
    assert len(fp) == 64


def test_tool_create_with_risk_labels_and_annotations() -> None:
    """Verify tool creation with multi-dimensional risk labels and annotations."""
    workspace_id = uuid.uuid4()
    server_id = uuid.uuid4()
    tool = ToolCreate(
        workspace_id=workspace_id,
        server_id=server_id,
        name="write_file",
        title="Write File to Disk",
        description="Creates or overwrites a file on the local filesystem.",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
        },
        annotations={"destructive_hint": True, "read_only_hint": False},
        classification_status=ToolClassificationStatus.SENSITIVE,
        risk_labels=["filesystem:write", "disk:modify", "filesystem:write"],  # duplicate check
    )
    assert tool.title == "Write File to Disk"
    assert tool.classification_status == ToolClassificationStatus.SENSITIVE
    # Risk labels must be deduplicated and sorted
    assert tool.risk_labels == ["disk:modify", "filesystem:write"]
    assert tool.annotations == {"destructive_hint": True, "read_only_hint": False}


def test_tool_name_validation() -> None:
    """Verify tool name format and length constraints."""
    assert validate_tool_name("search_documents") == "search_documents"
    assert validate_tool_name("api.v1.users:get") == "api.v1.users:get"
    assert validate_tool_name("my-tool-123") == "my-tool-123"

    with pytest.raises(AcpValidationError, match="cannot be empty"):
        validate_tool_name("   ")

    with pytest.raises(AcpValidationError, match="exceeds maximum length"):
        validate_tool_name("a" * 101)

    with pytest.raises(AcpValidationError, match="Invalid tool name format"):
        validate_tool_name("tool with spaces")

    with pytest.raises(AcpValidationError, match="Invalid tool name format"):
        validate_tool_name("tool$name#bad")


def test_tool_title_validation() -> None:
    """Verify tool title bounding and whitespace stripping."""
    assert validate_tool_title("  My Search Tool  ") == "My Search Tool"
    assert validate_tool_title(None) is None
    assert validate_tool_title("") is None
    assert validate_tool_title("   ") is None

    with pytest.raises(AcpValidationError, match="exceeds maximum length"):
        validate_tool_title("T" * 256)


def test_untrusted_description_bounding() -> None:
    """Verify that untrusted tool descriptions are bounded to prevent storage DoS."""
    safe_desc = "Standard tool description."
    assert validate_tool_description(safe_desc) == safe_desc

    oversized = "x" * (MAX_TOOL_DESCRIPTION_LENGTH + 1)
    with pytest.raises(AcpValidationError, match="exceeds maximum allowed length"):
        validate_tool_description(oversized)


def test_untrusted_input_schema_validation_success() -> None:
    """Verify valid JSON schema structures pass validation."""
    valid_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "required": ["name"],
    }
    validated = validate_tool_input_schema(valid_schema)
    assert validated == valid_schema


def test_untrusted_input_schema_non_dict_rejected() -> None:
    """Verify non-dictionary input schemas are rejected."""
    with pytest.raises(AcpValidationError, match="must be a dictionary"):
        validate_tool_input_schema("invalid string schema")

    with pytest.raises(AcpValidationError, match="must be a dictionary"):
        validate_tool_input_schema(["not", "a", "dict"])

    with pytest.raises(AcpValidationError, match="must be a dictionary"):
        validate_tool_input_schema(12345)


def test_untrusted_input_schema_size_limit_rejected() -> None:
    """Verify oversized input schema payloads (>64KB) are rejected."""
    props = {f"field_{i}": {"type": "string", "description": "A" * 1000} for i in range(70)}
    huge_schema = {
        "type": "object",
        "properties": props,
    }
    with pytest.raises(AcpValidationError, match="exceeds maximum permitted limit"):
        validate_tool_input_schema(huge_schema)


def test_untrusted_input_schema_deep_recursion_rejected() -> None:
    """Verify deeply nested schemas exceeding depth limit (10) are rejected."""
    nested: dict[str, Any] = {"level": 0}
    current = nested
    for i in range(1, 15):
        current["child"] = {"level": i}
        current = current["child"]

    with pytest.raises(AcpValidationError, match=r"nesting depth .* exceeds maximum"):
        validate_tool_input_schema(nested)


def test_risk_labels_validation() -> None:
    """Verify multi-dimensional independent risk labels formatting and deduplication."""
    labels = ["Filesystem:Read", "network:outbound ", "FILESYSTEM:READ", "s3:read_write"]
    cleaned = validate_risk_labels(labels)
    assert cleaned == ["filesystem:read", "network:outbound", "s3:read_write"]

    assert validate_risk_labels([]) == []
    assert validate_risk_labels(None) == []

    with pytest.raises(AcpValidationError, match="must be a list or set"):
        validate_risk_labels("not-a-list")

    with pytest.raises(AcpValidationError, match="Invalid risk label format"):
        validate_risk_labels(["invalid label with spaces"])

    with pytest.raises(AcpValidationError, match="Invalid risk label format"):
        validate_risk_labels(["bad$symbol"])


def test_deterministic_tool_fingerprinting() -> None:
    """Verify canonical fingerprinting: identical schemas produce identical SHA-256."""
    schema_1 = {
        "type": "object",
        "properties": {"b": {"type": "string"}, "a": {"type": "integer"}},
    }
    # Same content with different dictionary insertion order
    schema_2 = {
        "properties": {"a": {"type": "integer"}, "b": {"type": "string"}},
        "type": "object",
    }

    fp_1 = compute_tool_fingerprint("my_tool", schema_1, "A description", "Title")
    fp_2 = compute_tool_fingerprint("my_tool", schema_2, "A description", "Title")

    assert fp_1 == fp_2
    assert len(fp_1) == 64

    # Any change produces a distinct fingerprint
    fp_different = compute_tool_fingerprint("my_tool", schema_1, "Modified description", "Title")
    assert fp_different != fp_1


def test_deterministic_catalog_hash() -> None:
    """Verify cumulative catalog hash computation for change comparison."""
    tools = [
        {"name": "tool_b", "input_schema": {"type": "object"}, "description": "Tool B"},
        {"name": "tool_a", "input_schema": {"type": "object"}, "description": "Tool A"},
    ]
    # Reverse order should yield the same hash because compute_catalog_hash sorts tools
    tools_reversed = list(reversed(tools))

    hash_1 = compute_catalog_hash(tools)
    hash_2 = compute_catalog_hash(tools_reversed)

    assert hash_1 == hash_2
    assert len(hash_1) == 64

    # Modifying one tool changes the catalog hash
    tools_modified = [
        {"name": "tool_b", "input_schema": {"type": "object"}, "description": "Tool B Modified"},
        {"name": "tool_a", "input_schema": {"type": "object"}, "description": "Tool A"},
    ]
    hash_3 = compute_catalog_hash(tools_modified)
    assert hash_3 != hash_1


def test_tool_snapshot_create_and_read() -> None:
    """Verify ToolSnapshotCreate and ToolSnapshotRead schema behavior."""
    workspace_id = uuid.uuid4()
    server_id = uuid.uuid4()
    tools_data = [
        {
            "name": "calc",
            "title": "Calculator",
            "description": "Performs math",
            "input_schema": {"type": "object"},
        }
    ]

    snapshot_in = ToolSnapshotCreate(
        workspace_id=workspace_id,
        server_id=server_id,
        tools_data=tools_data,
        metadata={"discovery_protocol": "2024-11-05"},
    )
    assert snapshot_in.resolve_tool_count() == 1
    assert len(snapshot_in.resolve_catalog_hash()) == 64

    now = datetime.now(UTC)
    snapshot_read = ToolSnapshotRead(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        server_id=server_id,
        snapshot_at=now,
        catalog_hash=snapshot_in.resolve_catalog_hash(),
        tools_data=tools_data,
        tool_count=1,
        metadata={"discovery_protocol": "2024-11-05"},
        created_at=now,
        updated_at=now,
    )
    assert snapshot_read.tool_count == 1
    assert snapshot_read.catalog_hash == snapshot_in.resolve_catalog_hash()
    assert snapshot_read.metadata["discovery_protocol"] == "2024-11-05"


def test_tool_orm_representation() -> None:
    """Verify Tool and ToolSnapshot ORM model __repr__ formatting."""
    t_id = uuid.uuid4()
    s_id = uuid.uuid4()
    tool = Tool(
        id=t_id,
        workspace_id=uuid.uuid4(),
        server_id=s_id,
        name="test_tool",
        input_schema={},
        fingerprint="a" * 64,
        classification_status="safe",
        is_enabled=True,
    )
    repr_str = repr(tool)
    assert "test_tool" in repr_str
    assert "safe" in repr_str

    snapshot = ToolSnapshot(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        server_id=s_id,
        catalog_hash="b" * 64,
        tools_data=[],
        tool_count=0,
    )
    assert "tool_count=0" in repr(snapshot)
