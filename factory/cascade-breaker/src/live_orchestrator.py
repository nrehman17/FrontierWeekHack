from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from src.foundry_agents import AGENT_NAMES, run_foundry_agent
from src.orchestrator import build_decision_inputs, load_scenarios
from src.policy import evaluate_policy, load_policy
from src.schemas import (
    AgentStatus,
    Agents,
    CascadeState,
    DecisionState,
    GovernorState,
    Evidence,
    PolicyRef,
    ScoutState,
    SkepticState,
)


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Agent response must be a JSON object")
    return value


def invoke_validated(client, agent, prompt: str, model):
    raw = run_foundry_agent(client, agent, prompt)
    data = parse_json_response(raw)
    data["status"] = AgentStatus.COMPLETE.value

    # Foundry may emit JSON null for semantically empty list fields.
    # Normalize only fields whose strict schema requires a list.
    if model is SkepticState:
        for field in ("contradictory_evidence", "missing_evidence"):
            value = data.get(field)
            if value is None:
                data[field] = []
            elif isinstance(value, str):
                data[field] = [value]

    return model.model_validate(data)


def public_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in scenario.items()
        if key not in {"expected_decision", "skeptic_verdict", "false_positive_pattern"}
    }


def run_live_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    endpoint = os.environ["FOUNDRY_ENDPOINT"]
    client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )

    available = {a.name: a for a in client.agents.list()}
    agents = {
        role: available[name]
        for role, name in AGENT_NAMES.items()
    }

    scenario_input = public_scenario(scenario)

    scout = invoke_validated(
        client,
        agents["scout"],
        "Return JSON only with keys weak_signals, confidence, reason. "
        "Do not authorize or execute actions.\n"
        f"Scenario: {json.dumps(scenario_input)}",
        ScoutState,
    )

    cascade = invoke_validated(
        client,
        agents["cascade"],
        "Return JSON only with keys hypothesis, tipping_point_minutes, "
        "proposed_action, confidence, reason. Do not authorize or execute actions.\n"
        f"Scenario: {json.dumps(scenario_input)}\n"
        f"Scout: {scout.model_dump_json()}",
        CascadeState,
    )

    skeptic = invoke_validated(
        client,
        agents["skeptic"],
        "Return JSON only with keys verdict, false_positive_pattern, "
        "alternative_hypothesis, contradictory_evidence, missing_evidence, reason. "
        "verdict must be SUPPORT, CONTRADICT, or INSUFFICIENT. "
        "Use false_positive_pattern only when evidence supports a known pattern. "
        "You may block but cannot authorize or execute actions.\n"
        f"Scenario: {json.dumps(scenario_input)}\n"
        f"Scout: {scout.model_dump_json()}\n"
        f"Cascade: {cascade.model_dump_json()}",
        SkepticState,
    )

    governor = invoke_validated(
        client,
        agents["governor"],
        "Return JSON only with keys recommended_decision, confidence, reason. "
        "recommended_decision must be ACT_AUTO, ACT_HUMAN, ABSTAIN, or VETO. "
        "Your recommendation is advisory only; never claim authorization or execution.\n"
        f"Scenario: {json.dumps(scenario_input)}\n"
        f"Scout: {scout.model_dump_json()}\n"
        f"Cascade: {cascade.model_dump_json()}\n"
        f"Skeptic: {skeptic.model_dump_json()}",
        GovernorState,
    )

    policy = load_policy()
    state = DecisionState(
        run_id=str(uuid4()),
        scenario_id=scenario["scenario_id"],
        started_at=datetime.now(timezone.utc),
        policy=PolicyRef(
            policy_id=policy["policy_id"],
            policy_version=policy["policy_version"],
        ),
        evidence=Evidence(evidence_complete=True),
        decision_inputs=build_decision_inputs(scenario),
        agents=Agents(
            scout=scout,
            cascade=cascade,
            skeptic=skeptic,
            governor=governor,
        ),
    )

    result = evaluate_policy(state, policy)
    state.gate.decision = result.decision
    state.gate.authorized = result.authorized
    state.gate.reason_code = result.reason_code
    state.final_decision = result.decision
    state.completed_at = datetime.now(timezone.utc)

    return {
        "run_id": state.run_id,
        "scenario_id": scenario["scenario_id"],
        "synthetic": bool(scenario["synthetic"]),
        "governor_recommendation": governor.recommended_decision.value,
        "policy_decision": result.decision.value,
        "authorized": result.authorized,
        "reason_code": result.reason_code,
        "state": state.model_dump(mode="json"),
    }


def main() -> int:
    scenario = load_scenarios()[0]
    record = run_live_scenario(scenario)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
