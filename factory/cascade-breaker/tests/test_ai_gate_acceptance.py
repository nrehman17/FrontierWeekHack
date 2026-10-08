from datetime import datetime, timezone

from src.evidence import AIClaim, validate_ai_claim
from src.orchestrator import build_decision_inputs
from src.policy import evaluate_policy, load_policy
from src.schemas import (
    ActionTier,
    Agents,
    CascadeState,
    Decision,
    DecisionInputs,
    DecisionState,
    Evidence,
    GovernorState,
    PolicyRef,
    ScoutState,
    SkepticState,
)


def make_state(inputs: DecisionInputs, governor_decision: Decision) -> DecisionState:
    return DecisionState(
        run_id="redteam-acceptance",
        scenario_id="REDTEAM_AI_GATE",
        started_at=datetime.now(timezone.utc).isoformat(),
        policy=PolicyRef(
            policy_id="test-policy",
            policy_version="1.0",
        ),
        evidence=Evidence(evidence_complete=True),
        decision_inputs=inputs,
        agents=Agents(
            scout=ScoutState(
                status="COMPLETE",
                weak_signals=["supplier disruption"],
                confidence=inputs.confidence_p,
                reason="adversarial test",
            ),
            cascade=CascadeState(
                status="COMPLETE",
                hypothesis="supplier disruption may propagate",
                tipping_point_minutes=inputs.predicted_lead_minutes,
                proposed_action="reroute supplier",
                confidence=inputs.confidence_p,
                reason="adversarial test",
            ),
            skeptic=SkepticState(
                status="COMPLETE",
                verdict="SUPPORT",
                false_positive_pattern=None,
                alternative_hypothesis=None,
                contradictory_evidence=[],
                missing_evidence=[],
                reason="no registered false-positive pattern",
            ),
            governor=GovernorState(
                status="COMPLETE",
                recommended_decision=governor_decision,
                confidence=0.99,
                reason="adversarial Governor recommendation",
            ),
        ),
    )


def decision_inputs_from_ai(
    scenario: dict,
    confidence: float,
    lead_minutes: float,
) -> DecisionInputs:
    claim = AIClaim(
        confidence_p=confidence,
        predicted_lead_minutes=lead_minutes,
        evidence_ids=["scenario_evidence"],
    )

    validate_ai_claim(claim, {"scenario_evidence"})

    return build_decision_inputs(
        scenario,
        ai_claim=claim,
    )


def test_adversarial_ai_reasoning_should_change_policy_outcome():
    """
    Same trusted scenario, different validated AI reasoning.

    AI-A:
        confidence=0.86
        lead=120 minutes
        => ACT_AUTO

    AI-B:
        confidence=0.58
        lead=35 minutes
        => ABSTAIN

    The test verifies that validated AI claims actually influence
    deterministic policy inputs and therefore the policy outcome.
    """

    scenario = {
        "scenario_id": "REDTEAM_AI_GATE",
        "action_latency_minutes": 15.0,
        "safety_margin_minutes": 15.0,
        "action_tier": "T1",
        "false_action_cost_cf": 5.0,
        "inaction_cost_ci": 100.0,
    }

    inputs_a = decision_inputs_from_ai(
        scenario,
        confidence=0.86,
        lead_minutes=120.0,
    )

    inputs_b = decision_inputs_from_ai(
        scenario,
        confidence=0.58,
        lead_minutes=35.0,
    )

    assert inputs_a != inputs_b
    assert inputs_a.confidence_p == 0.86
    assert inputs_a.predicted_lead_minutes == 120.0
    assert inputs_a.usable_lead_time_minutes == 90.0

    assert inputs_b.confidence_p == 0.58
    assert inputs_b.predicted_lead_minutes == 35.0
    assert inputs_b.usable_lead_time_minutes == 5.0

    result_a = evaluate_policy(
        make_state(inputs_a, Decision.ACT_AUTO),
        load_policy(),
    )
    result_b = evaluate_policy(
        make_state(inputs_b, Decision.ACT_AUTO),
        load_policy(),
    )

    assert result_a.decision == Decision.ACT_AUTO
    assert result_a.authorized is True

    assert result_b.decision == Decision.ABSTAIN
    assert result_b.authorized is False


def test_malicious_governor_cannot_override_policy():
    """
    The Governor explicitly recommends ACT_AUTO with 0.99 confidence.

    The deterministic policy must still return ABSTAIN because the
    decision inputs are in the policy's abstention band.
    """

    scenario = {
        "scenario_id": "REDTEAM_AI_GATE",
        "action_latency_minutes": 15.0,
        "safety_margin_minutes": 15.0,
        "action_tier": "T1",
        "false_action_cost_cf": 5.0,
        "inaction_cost_ci": 100.0,
    }

    ai_b = decision_inputs_from_ai(
        scenario,
        confidence=0.58,
        lead_minutes=35.0,
    )

    state = make_state(
        inputs=ai_b,
        governor_decision=Decision.ACT_AUTO,
    )

    result = evaluate_policy(
        state,
        load_policy(),
    )

    assert result.decision == Decision.ABSTAIN
    assert result.authorized is False
