from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.agents import run_cascade, run_governor, run_scout, run_skeptic
from src.policy import evaluate_policy, load_policy
from src.schemas import (
    ActionTier,
    Agents,
    DecisionInputs,
    DecisionState,
    Evidence,
    PolicyRef,
)


ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = ROOT / "data" / "scenarios.json"
LEDGER_PATH = ROOT / "ledger" / "runs.jsonl"


def load_scenarios() -> list[dict[str, Any]]:
    with SCENARIOS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)["scenarios"]


def build_decision_inputs(scenario: dict[str, Any]) -> DecisionInputs:
    predicted_lead = float(scenario["predicted_lead_minutes"])
    latency = float(scenario["action_latency_minutes"])
    safety_margin = float(scenario["safety_margin_minutes"])
    cf = float(scenario["false_action_cost_cf"])
    ci = float(scenario["inaction_cost_ci"])

    usable_lead = max(0.0, predicted_lead - latency - safety_margin)
    cf_ci_ratio = cf / ci if ci > 0 else float("inf")

    return DecisionInputs(
        confidence_p=float(scenario["confidence_p"]),
        predicted_lead_minutes=predicted_lead,
        action_latency_minutes=latency,
        safety_margin_minutes=safety_margin,
        usable_lead_time_minutes=usable_lead,
        action_tier=ActionTier(scenario["action_tier"]),
        false_action_cost_cf=cf,
        inaction_cost_ci=ci,
        cf_ci_ratio=cf_ci_ratio,
    )


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)

    scout = run_scout(scenario)
    cascade = run_cascade(scenario, scout)
    skeptic = run_skeptic(scenario, cascade)
    governor = run_governor(scenario, scout, cascade, skeptic)

    policy = load_policy()
    decision_inputs = build_decision_inputs(scenario)

    state = DecisionState(
        run_id=run_id,
        scenario_id=scenario["scenario_id"],
        started_at=started_at,
        policy=PolicyRef(
            policy_id=policy["policy_id"],
            policy_version=policy["policy_version"],
        ),
        evidence=Evidence(
            evidence_complete=True,
        ),
        decision_inputs=decision_inputs,
        agents=Agents(
            scout=scout,
            cascade=cascade,
            skeptic=skeptic,
            governor=governor,
        ),
    )

    result = evaluate_policy(state, policy)
    state.final_decision = result.decision
    state.completed_at = datetime.now(timezone.utc)

    record = {
        "run_id": run_id,
        "scenario_id": scenario["scenario_id"],
        "synthetic": bool(scenario["synthetic"]),
        "expected_decision": scenario["expected_decision"],
        "governor_recommendation": governor.recommended_decision.value,
        "policy_decision": result.decision.value,
        "authorized": result.authorized,
        "reason_code": result.reason_code,
        "match": result.decision.value == scenario["expected_decision"],
        "state": state.model_dump(mode="json"),
    }

    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")

    return record


def main() -> int:
    scenarios = load_scenarios()
    all_match = True

    for scenario in scenarios:
        record = run_scenario(scenario)
        all_match = all_match and record["match"]

        print(
            f"{record['scenario_id']}: "
            f"expected={record['expected_decision']} "
            f"policy={record['policy_decision']} "
            f"authorized={record['authorized']} "
            f"match={record['match']}"
        )

    return 0 if all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
