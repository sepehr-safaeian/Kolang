from __future__ import annotations

from acp_core.common.types import PolicyId, PrincipalKind
from acp_core.policy.models import (
    PolicyCondition,
    PolicyDecision,
    PolicyEffect,
    PolicyEvaluationInput,
    PolicyRule,
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
