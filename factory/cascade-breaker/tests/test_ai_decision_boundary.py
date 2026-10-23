import pytest

from src.evidence import claim_from_cascade
from src.orchestrator import build_decision_inputs


@pytest.fixture
def scenario():
    return {
        "confidence_p": 0.95,
        "predicted_lead_minutes": 60.0,
        "action_latency_minutes": 10.0,
        "safety_margin_minutes": 5.0,
        "false_action_cost_cf": 20.0,
        "inaction_cost_ci": 10.0,
        "action_tier": "T1",
    }


def test_valid_cascade_claim_overrides_scenario(scenario):
    claim = claim_from_cascade(
        confidence_p=0.72,
        predicted_lead_minutes=40.0,
    )

    result = build_decision_inputs(scenario, ai_claim=claim)

    assert result.confidence_p == pytest.approx(0.72)
    assert result.predicted_lead_minutes == pytest.approx(40.0)
    assert result.usable_lead_time_minutes == pytest.approx(25.0)


def test_missing_claim_fails_closed_when_required(scenario):
    result = build_decision_inputs(
        scenario,
        ai_claim=None,
        require_ai_claim=True,
    )

    assert result.confidence_p is None
    assert result.predicted_lead_minutes is None
    assert result.usable_lead_time_minutes is None


@pytest.mark.parametrize(
    ("confidence", "lead"),
    [
        (None, 40.0),
        (0.8, None),
        (float("nan"), 40.0),
        (0.8, -1.0),
    ],
)
def test_invalid_cascade_claim_fails_closed_when_required(
    scenario, confidence, lead
):
    claim = claim_from_cascade(
        confidence_p=confidence,
        predicted_lead_minutes=lead,
    )

    result = build_decision_inputs(
        scenario,
        ai_claim=claim,
        require_ai_claim=True,
    )

    assert result.confidence_p is None
    assert result.predicted_lead_minutes is None
    assert result.usable_lead_time_minutes is None
