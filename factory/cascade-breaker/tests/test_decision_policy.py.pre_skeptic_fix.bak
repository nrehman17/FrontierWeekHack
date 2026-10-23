from datetime import datetime, timezone

from src.schemas import (
    ActionTier,
    Decision,
    DecisionInputs,
    DecisionState,
    Evidence,
    PolicyRef,
    SkepticVerdict,
)


def make_state(
    run_id,
    scenario_id,
    p,
    usable_lead,
    action_latency,
    tier,
    cf,
    ci,
    skeptic_false_positive=False,
):
    state = DecisionState(
        run_id=run_id,
        scenario_id=scenario_id,
        started_at=datetime.now(timezone.utc),
        policy=PolicyRef(
            policy_id="cascade-breaker-decision-policy",
            policy_version="1.0",
        ),
        evidence=Evidence(evidence_complete=True),
        decision_inputs=DecisionInputs(
            confidence_p=p,
            predicted_lead_minutes=usable_lead,
            action_latency_minutes=action_latency,
            safety_margin_minutes=0,
            usable_lead_time_minutes=usable_lead,
            action_tier=ActionTier(tier),
            false_action_cost_cf=cf,
            inaction_cost_ci=ci,
            cf_ci_ratio=cf / ci,
        ),
    )

    if skeptic_false_positive:
        state.agents.skeptic.verdict = SkepticVerdict.CONTRADICT
        state.agents.skeptic.false_positive_pattern = "stable-straggler"

    return state


def test_s1_auto_act():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-S1-ACT", "S1_ACT",
        p=0.83,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.ACT_AUTO
    assert result.authorized is True
    assert result.reason_code == "AUTO_ACT_THRESHOLD_MET"


def test_s2_skeptic_false_positive_forces_veto():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-S2-VETO", "S2_VETO",
        p=0.87,
        usable_lead=180,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
        skeptic_false_positive=True,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.VETO
    assert result.authorized is False
    assert result.reason_code == "SKEPTIC_FALSE_POSITIVE_MATCH"


def test_s3_ambiguous_evidence_abstains():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-S3-ABSTAIN", "S3_ABSTAIN",
        p=0.50,
        usable_lead=90,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.ABSTAIN
    assert result.authorized is False
    assert result.reason_code == "CONFIDENCE_INSUFFICIENT"


def test_below_auto_act_confidence_does_not_auto_act():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-BOUNDARY-P",
        "BOUNDARY",
        p=0.799999,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision != Decision.ACT_AUTO
    assert result.authorized is False


def test_t3_always_vetoes():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-T3",
        "BOUNDARY",
        p=0.99,
        usable_lead=1000,
        action_latency=1,
        tier="T3",
        cf=1,
        ci=1000,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.VETO
    assert result.authorized is False
    assert result.reason_code == "T3_ACTION_PROHIBITED"


def test_cf_ci_above_limit_cannot_auto_act():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-ECONOMICS",
        "BOUNDARY",
        p=0.95,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=11,
        ci=100,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision != Decision.ACT_AUTO
    assert result.authorized is False


def test_skeptic_veto_beats_very_high_confidence():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-SKEPTIC-AUTHORITY",
        "BOUNDARY",
        p=0.99,
        usable_lead=1000,
        action_latency=1,
        tier="T1",
        cf=1,
        ci=1000,
        skeptic_false_positive=True,
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.VETO
    assert result.authorized is False
    assert result.reason_code == "SKEPTIC_FALSE_POSITIVE_MATCH"


def test_unregistered_skeptic_pattern_cannot_force_veto():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-UNREGISTERED-SKEPTIC-PATTERN",
        "S1_ACT",
        p=0.83,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )
    state.agents.skeptic.verdict = SkepticVerdict.CONTRADICT
    state.agents.skeptic.false_positive_pattern = (
        "Synthetic scenario parameters driving overfitted conclusions based on weak signals."
    )

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.ACT_AUTO
    assert result.authorized is True
    assert result.reason_code == "AUTO_ACT_THRESHOLD_MET"


def test_scenario_label_cannot_change_decision():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-LABEL-LEAK",
        "S1_ACT",
        p=0.83,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    first = evaluate_policy(state, load_policy())

    # Deliberately lie in the scenario label.
    state.scenario_id = "S2_VETO_EXPECTED"

    second = evaluate_policy(state, load_policy())

    assert first.decision == Decision.ACT_AUTO
    assert second.decision == Decision.ACT_AUTO
    assert first.reason_code == second.reason_code


def test_governor_cannot_force_act():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-GOVERNOR-NO-AUTHORITY",
        "MUTATION",
        p=0.50,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    # Simulate an LLM Governor demanding ACT.
    state.agents.governor.recommended_decision = Decision.ACT_AUTO
    state.agents.governor.confidence = 0.99

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.ABSTAIN
    assert result.authorized is False
    assert result.reason_code == "CONFIDENCE_INSUFFICIENT"


def test_mutating_policy_input_changes_gate_result():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-POLICY-MUTATION",
        "MUTATION",
        p=0.83,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    before = evaluate_policy(state, load_policy())
    assert before.decision == Decision.ACT_AUTO

    # Change a real gate input, not a label or LLM opinion.
    state.decision_inputs.false_action_cost_cf = 20
    state.decision_inputs.cf_ci_ratio = 0.20

    after = evaluate_policy(state, load_policy())

    assert after.decision != Decision.ACT_AUTO
    assert after.authorized is False


def test_skeptic_can_block_but_cannot_force_act():
    from src.policy import evaluate_policy, load_policy

    state = make_state(
        "TEST-SKEPTIC-NO-FORCE",
        "MUTATION",
        p=0.50,
        usable_lead=120,
        action_latency=30,
        tier="T1",
        cf=5,
        ci=100,
    )

    state.agents.skeptic.verdict = SkepticVerdict.SUPPORT

    result = evaluate_policy(state, load_policy())

    assert result.decision == Decision.ABSTAIN
    assert result.authorized is False
