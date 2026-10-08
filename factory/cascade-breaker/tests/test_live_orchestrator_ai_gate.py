from types import SimpleNamespace

from src import live_orchestrator
from src.schemas import (
    CascadeState,
    GovernorState,
    ScoutState,
    SkepticState,
)


def test_live_orchestrator_uses_cascade_output_for_gate_inputs(monkeypatch):
    scenario = {
        "scenario_id": "LIVE_AI_GATE",
        "synthetic": True,
        "confidence_p": 0.86,
        "predicted_lead_minutes": 120.0,
        "action_latency_minutes": 15.0,
        "safety_margin_minutes": 15.0,
        "action_tier": "T1",
        "false_action_cost_cf": 5.0,
        "inaction_cost_ci": 100.0,
    }

    scout = ScoutState(
        status="COMPLETE",
        weak_signals=["supplier disruption"],
        confidence=0.86,
        reason="test",
    )

    cascade = CascadeState(
        status="COMPLETE",
        hypothesis="adversarial live-path test",
        tipping_point_minutes=35.0,
        proposed_action="reroute supplier",
        confidence=0.58,
        reason="test",
    )

    skeptic = SkepticState(
        status="COMPLETE",
        verdict="SUPPORT",
        false_positive_pattern=None,
        alternative_hypothesis=None,
        contradictory_evidence=[],
        missing_evidence=[],
        reason="test",
    )

    governor = GovernorState(
        status="COMPLETE",
        recommended_decision="ACT_AUTO",
        confidence=0.99,
        reason="advisory test",
    )

    invocation = {
        "agent_name": "test-agent",
        "response_id": "test-response",
        "status": "completed",
        "conversation_id": "test-conversation",
        "model": "test-model",
    }

    responses = {
        "scout": (scout, invocation),
        "cascade": (cascade, invocation),
        "skeptic": (skeptic, invocation),
        "governor": (governor, invocation),
    }

    def fake_invoke_validated(
        client,
        agent,
        prompt,
        model,
        *,
        tracer,
        run_id,
        scenario_id,
        role,
    ):
        return responses[role]

    class FakeAgents:
        def list(self):
            return [
                SimpleNamespace(name="cascade-breaker-scout"),
                SimpleNamespace(name="cascade-breaker-cascade"),
                SimpleNamespace(name="cascade-breaker-skeptic"),
                SimpleNamespace(name="cascade-breaker-governor"),
            ]

    class FakeClient:
        def __init__(self):
            self.agents = FakeAgents()

    class FakeSpan:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setenv("FOUNDRY_ENDPOINT", "https://test-foundry.example")

    monkeypatch.setattr(
        live_orchestrator,
        "AIProjectClient",
        lambda endpoint, credential: FakeClient(),
    )
    monkeypatch.setattr(
        live_orchestrator,
        "DefaultAzureCredential",
        lambda: object(),
    )
    monkeypatch.setattr(
        live_orchestrator,
        "configure_foundry_tracer",
        lambda client: None,
    )
    monkeypatch.setattr(
        live_orchestrator,
        "traced_span",
        lambda *args, **kwargs: FakeSpan(),
    )
    monkeypatch.setattr(
        live_orchestrator,
        "set_span_attributes",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        live_orchestrator,
        "invoke_validated",
        fake_invoke_validated,
    )
    monkeypatch.setattr(
        live_orchestrator,
        "flush_traces",
        lambda: True,
    )

    record = live_orchestrator.run_live_scenario(scenario)

    inputs = record["state"]["decision_inputs"]

    assert inputs["confidence_p"] == 0.58
    assert inputs["predicted_lead_minutes"] == 35.0
    assert inputs["usable_lead_time_minutes"] == 5.0

    # Regression guard: the scenario fixture must not supply these
    # AI-owned gate inputs once a validated Cascade claim exists.
    assert inputs["confidence_p"] != scenario["confidence_p"]
    assert inputs["predicted_lead_minutes"] != scenario["predicted_lead_minutes"]
