import json
import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.schemas import ActionTier, Decision, DecisionState, SkepticVerdict


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
    supplied_ratio = inputs.cf_ci_ratio
    false_action_cost = inputs.false_action_cost_cf
    inaction_cost = inputs.inaction_cost_ci

    required = (p, usable_lead, latency, tier, supplied_ratio, false_action_cost, inaction_cost)
    if any(value is None for value in required):
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="REQUIRED_INPUT_MISSING",
        )

    numeric_values = (p, usable_lead, latency, supplied_ratio, false_action_cost, inaction_cost)
    if any(not math.isfinite(value) for value in numeric_values):
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="NON_FINITE_DECISION_INPUT",
        )
    if p < 0 or p > 1 or usable_lead < 0 or latency < 0 or false_action_cost < 0 or inaction_cost <= 0:
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="INVALID_DECISION_INPUT",
        )

    # Recompute the ratio from its source values; never trust a contradictory
    # precomputed ratio supplied by an upstream agent or caller.
    ratio = false_action_cost / inaction_cost
    if not math.isclose(supplied_ratio, ratio, rel_tol=1e-6, abs_tol=1e-9):
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="INCONSISTENT_COST_RATIO",
        )

    # Highest authority: deterministic hard VETO conditions.
    if tier.value in policy["veto"]["prohibited_tiers"]:
        return PolicyResult(
            decision=Decision.VETO,
            authorized=False,
            reason_code="T3_ACTION_PROHIBITED",
        )

    known_false_positive_patterns = {
        str(pattern).strip().casefold()
        for pattern in policy["veto"].get("known_false_positive_patterns", [])
    }
    skeptic_false_positive_pattern = (
        skeptic.false_positive_pattern.strip().casefold()
        if skeptic.false_positive_pattern
        else None
    )

    if (
        policy["veto"]["skeptic_false_positive_match"]
        and skeptic_false_positive_pattern in known_false_positive_patterns
    ):
        return PolicyResult(
            decision=Decision.VETO,
            authorized=False,
            reason_code="SKEPTIC_FALSE_POSITIVE_MATCH",
        )

    # Uncertainty is not a prohibition. Low confidence therefore ABSTAINS;
    # VETO is reserved for deterministic prohibitions or registered veto rules.
    if p < policy["abstain"]["minimum_confidence_for_evaluation"]:
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="CONFIDENCE_BELOW_MINIMUM",
        )

    # A model's skeptical assessment cannot authorize action. Contradiction,
    # insufficient analysis, or a missing verdict requires abstention.
    if skeptic.verdict != SkepticVerdict.SUPPORT:
        reason = (
            "SKEPTIC_CONTRADICTS"
            if skeptic.verdict == SkepticVerdict.CONTRADICT
            else "SKEPTIC_INSUFFICIENT"
        )
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code=reason,
        )

    # Fail closed when required evidence has not been verified as complete.
    # Keep hard vetoes above this check so their precedence is unchanged.
    if not state.evidence.evidence_complete:
        return PolicyResult(
            decision=Decision.ABSTAIN,
            authorized=False,
            reason_code="CRITICAL_EVIDENCE_INCOMPLETE",
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

    # Auto ACT. This authorizes only the policy outcome; it does not execute
    # an operational action or establish that an action succeeded.
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

    return PolicyResult(
        decision=Decision.ABSTAIN,
        authorized=False,
        reason_code="ACT_GATE_NOT_MET",
    )
