import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.schemas import ActionTier, Decision, DecisionState


class PolicyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    authorized: bool
    reason_code: str


def load_policy() -> dict:
    policy_path = Path(__file__).resolve().parent.parent / "decision_policy.json"

    with policy_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_policy(state: DecisionState, policy: dict) -> PolicyResult:
    inputs = state.decision_inputs
    skeptic = state.agents.skeptic

    p = inputs.confidence_p
    usable_lead = inputs.usable_lead_time_minutes
    latency = inputs.action_latency_minutes
    tier = inputs.action_tier
    ratio = inputs.cf_ci_ratio

    if p is None or usable_lead is None or latency is None or tier is None or ratio is None:
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="REQUIRED_INPUT_MISSING",
        )

    # Highest authority: hard VETO conditions.
    if tier.value in policy["veto"]["prohibited_tiers"]:
        return PolicyResult(
            decision=Decision.VETO,
            authorized=False,
            reason_code="T3_ACTION_PROHIBITED",
        )

    if (
        policy["veto"]["skeptic_false_positive_match"]
        and skeptic.false_positive_pattern is not None
    ):
        return PolicyResult(
            decision=Decision.VETO,
            authorized=False,
            reason_code="SKEPTIC_FALSE_POSITIVE_MATCH",
        )

    if p < policy["veto"]["confidence_below"]:
        return PolicyResult(
            decision=Decision.VETO,
            authorized=False,
            reason_code="CONFIDENCE_BELOW_VETO_THRESHOLD",
        )

    # Frozen ABSTAIN confidence band takes precedence over ACT evaluation.
    abstain = policy["abstain"]
    if abstain["min_confidence"] <= p < abstain["max_confidence_exclusive"]:
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="CONFIDENCE_INSUFFICIENT",
        )

    # Human ACT.
    human = policy["human_act"]
    if (
        tier == ActionTier(human["required_tier"])
        and p >= human["min_confidence"]
        and usable_lead >= human["min_usable_lead_minutes"]
    ):
        return PolicyResult(
            decision=Decision.ACT_HUMAN,
            authorized=False,
            reason_code="HUMAN_ACT_REQUIRED",
        )

    # Auto ACT.
    auto = policy["auto_act"]
    if (
        tier == ActionTier(auto["required_tier"])
        and p >= auto["min_confidence"]
        and usable_lead >= auto["min_lead_latency_multiple"] * latency
        and ratio <= auto["max_cf_ci_ratio"]
    ):
        return PolicyResult(
            decision=Decision.ACT_AUTO,
            authorized=True,
            reason_code="AUTO_ACT_THRESHOLD_MET",
        )

    # Evidence is plausible but one or more ACT gates were not met.
    return PolicyResult(
        decision=Decision.ABSTAIN,
        authorized=False,
        reason_code="ACT_GATE_NOT_MET",
    )
