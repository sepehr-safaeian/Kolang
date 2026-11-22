"""
Unit tests for ACP-012 Policy and Policy Version Models.

Verifies:
1. PolicyStatus and PolicyVersionStatus lifecycle enums.
2. Deterministic SHA-256 checksum computation and change sensitivity.
3. Policy slug format validation and whitespace normalization.
4. Segregation between Policy Draft and Published states (is_draft vs is_active).
5. Exact Policy Version capture in PolicyDecision (Rule 2).
6. Immutability enforcement: modifying published PolicyVersion raises
   PolicyVersionImmutableError (Rule 1).
7. Backward compatibility with existing internal policy models (PolicyRule, PolicyCondition).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from acp_core.common.errors import PolicyVersionImmutableError
from acp_core.common.types import DecisionEffect, PolicyId
from acp_core.db.base import Base
from acp_core.policy.models import (
    Policy,
    PolicyBase,
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyRead,
    PolicyRule,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    compute_policy_checksum,
    create_decision_for_version,
)


def test_policy_effect_enum() -> None:
    assert PolicyEffect.ALLOW == "allow"
    assert PolicyEffect.DENY == "deny"
    assert PolicyEffect.CONDITIONAL == "conditional"


def test_policy_decision_creation() -> None:
    decision = PolicyDecision(
        effect=PolicyEffect.ALLOW,
        policy_id="pol-001",
        reason="Admin principal allowed",
    )
    assert decision.effect == PolicyEffect.ALLOW
    assert decision.policy_id == "pol-001"
    assert len(decision.conditions) == 0


def test_conditional_policy_decision() -> None:
    cond = PolicyCondition(
        type="approval",
        params={"approvers": ["security-team", "lead"]},
    )
    decision = PolicyDecision(
        effect=PolicyEffect.CONDITIONAL,
        reason="Requires team signoff",
        conditions=[cond],
    )
    assert decision.effect == PolicyEffect.CONDITIONAL
    assert len(decision.conditions) == 1
    assert decision.conditions[0].type == "approval"


def test_policy_rule_independent_of_rpc() -> None:
    rule = PolicyRule(
        id=PolicyId("rule-db-read"),
        name="Database read access",
        effect=PolicyEffect.ALLOW,
        principals=["user:*", "agent:reader-*"],
        servers=["postgres-*"],
        tools=["query", "select"],
    )
    assert rule.enabled is True
    assert "query" in rule.tools


# ── ACP-012 New Model Tests ──────────────────────────────────────────────────


def test_policy_status_enums() -> None:
    assert PolicyStatus.DRAFT == "draft"
    assert PolicyStatus.ACTIVE == "active"
    assert PolicyStatus.DEPRECATED == "deprecated"
    assert PolicyStatus.ARCHIVED == "archived"

    assert PolicyVersionStatus.PUBLISHED == "published"
    assert PolicyVersionStatus.SUPERSEDED == "superseded"
    assert PolicyVersionStatus.ARCHIVED == "archived"


def test_policy_checksum_computation() -> None:
    code = "package kolang.authz\ndefault allow := false\n"
    expected = hashlib.sha256(code.encode("utf-8")).hexdigest()

    checksum = compute_policy_checksum(code)
    assert checksum == expected
    assert len(checksum) == 64

    # With bundle reference
    bundle = "oci://registry.kolang.internal/policies/sec:v1"
    raw_payload = code.encode("utf-8") + b"\x00" + bundle.encode("utf-8")
    expected_with_bundle = hashlib.sha256(raw_payload).hexdigest()
    checksum_bundle = compute_policy_checksum(code, bundle)
    assert checksum_bundle == expected_with_bundle
    assert checksum_bundle != checksum


def test_policy_slug_validation() -> None:
    # Valid slugs
    p1 = PolicyBase(name="Tool Approval Policy", slug="tool-approval-v1")
    assert p1.slug == "tool-approval-v1"

    p2 = PolicyBase(name="DB Read Policy", slug="db-read-policy")
    assert p2.slug == "db-read-policy"

    p3 = PolicyBase(name="Upper", slug="UPPERCASE-SLUG")
    assert p3.slug == "uppercase-slug"

    # Invalid slugs
    with pytest.raises(ValueError, match="Invalid slug format"):
        PolicyBase(name="Bad", slug="-leading-hyphen")

    with pytest.raises(ValueError, match="Invalid slug format"):
        PolicyBase(name="Bad", slug="trailing-hyphen-")

    with pytest.raises(ValueError, match="Invalid slug format"):
        PolicyBase(name="Bad", slug="invalid_underscore")

    with pytest.raises(ValueError, match="Invalid slug format"):
        PolicyBase(name="Bad", slug="has spaces")


def test_policy_draft_vs_published_state() -> None:
    """AC: Policy Draft is distinct from Policy Published and is not active by default."""
    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    now = datetime.now(UTC)

    # Draft policy
    draft = PolicyRead(
        id=pol_id,
        workspace_id=ws_id,
        name="Security Policy",
        slug="sec-pol",
        description="Initial draft",
        status=PolicyStatus.DRAFT,
        draft_rego="package kolang\ndefault allow := false",
        draft_bundle_reference=None,
        active_version_id=None,
        active_version_number=None,
        created_by="user:admin@kolang.local",
        updated_by=None,
        created_at=now,
        updated_at=now,
    )
    assert draft.is_draft is True
    assert draft.is_active is False
    assert draft.active_version_id is None

    # Published policy
    ver_id = uuid.uuid4()
    published = PolicyRead(
        id=pol_id,
        workspace_id=ws_id,
        name="Security Policy",
        slug="sec-pol",
        description="Published version 1",
        status=PolicyStatus.ACTIVE,
        draft_rego="package kolang\ndefault allow := false",
        draft_bundle_reference=None,
        active_version_id=ver_id,
        active_version_number=1,
        created_by="user:admin@kolang.local",
        updated_by="user:admin@kolang.local",
        created_at=now,
        updated_at=now,
    )
    assert published.is_draft is False
    assert published.is_active is True
    assert published.active_version_number == 1


def test_decision_records_exact_policy_version() -> None:
    """Enforces ACP-012 Rule 2: Every decision must capture the precise policy version."""
    policy_id = uuid.uuid4()
    version_num = 3

    decision = create_decision_for_version(
        policy_id=policy_id,
        version=version_num,
        decision=DecisionEffect.ALLOW,
        reason_code="AUTHZ_POLICY_ALLOW",
        reason_message="Access granted by security rule",
    )

    assert decision.policy_id == str(policy_id)
    assert decision.version == "3"
    assert decision.effect == "allow"
    assert decision.reason_code == "AUTHZ_POLICY_ALLOW"


def test_policy_version_immutability_enforced() -> None:
    """Enforces ACP-012 Rule 1: Published policy versions are strictly immutable."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        ws_id = uuid.uuid4()
        pol_id = uuid.uuid4()
        ver_id = uuid.uuid4()

        pol = Policy(
            id=pol_id,
            workspace_id=ws_id,
            name="Immutable Policy",
            slug="immutable-policy",
            status=PolicyStatus.ACTIVE.value,
            created_by="admin@kolang.local",
        )
        session.add(pol)

        pv = PolicyVersion(
            id=ver_id,
            policy_id=pol_id,
            workspace_id=ws_id,
            version=1,
            rego_source="package kolang.authz\ndefault allow := false",
            checksum=compute_policy_checksum("package kolang.authz\ndefault allow := false"),
            description="Initial version",
            status=PolicyVersionStatus.PUBLISHED.value,
            published_by="admin@kolang.local",
        )
        session.add(pv)
        session.commit()

        # Attempt to mutate rego_source on published version
        pv.rego_source = "package kolang.authz\ndefault allow := true"

        with pytest.raises(
            PolicyVersionImmutableError,
            match="immutable: modification of 'rego_source' is forbidden",
        ):
            session.commit()

        session.rollback()

        # Attempt to mutate version number
        pv.version = 2
        with pytest.raises(
            PolicyVersionImmutableError,
            match="immutable: modification of 'version' is forbidden",
        ):
            session.commit()
