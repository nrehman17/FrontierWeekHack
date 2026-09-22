"""Deterministic quality evaluation for Cascade Breaker.

Evaluates the frozen synthetic decision scenarios without invoking live agents
and without writing to the operational ledger.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.orchestrator import build_decision_inputs, load_scenarios
from src.policy import evaluate_policy, load_policy
from src.schemas import (
    Decision,
    DecisionState,
    Evidence,
    PolicyRef,
    SkepticVerdict,
)


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "evaluation"
REPORT_PATH = OUTPUT_DIR / "gate4b_policy_evaluation.json"
DATASET_PATH = OUTPUT_DIR / "gate4b_policy_evaluation.jsonl"

ACT_DECISIONS = {Decision.ACT_AUTO, Decision.ACT_HUMAN}


def evaluate_scenario(scenario: dict[str, Any], policy: dict) -> dict[str, Any]:
    state = DecisionState(
        run_id=f"EVAL-{uuid4()}",
        scenario_id=scenario["scenario_id"],
        started_at=datetime.now(timezone.utc),
        policy=PolicyRef(
            policy_id=policy["policy_id"],
            policy_version=policy["policy_version"],
        ),
        evidence=Evidence(evidence_complete=True),
        decision_inputs=build_decision_inputs(scenario),
    )

    # Ground-truth Skeptic condition is part of the frozen synthetic fixture.
    state.agents.skeptic.verdict = SkepticVerdict(scenario["skeptic_verdict"])
    state.agents.skeptic.false_positive_pattern = scenario["false_positive_pattern"]

    result = evaluate_policy(state, policy)

    expected = Decision(scenario["expected_decision"])
    actual = result.decision

    expected_action = expected in ACT_DECISIONS
    actual_action = actual in ACT_DECISIONS

    correct = actual == expected
    false_action = actual_action and not expected_action
    unnecessary_abstention = actual == Decision.ABSTAIN and expected != Decision.ABSTAIN
    unsafe_authorization = result.authorized and expected != Decision.ACT_AUTO

    useful_lead = None
    if (
        correct
        and expected == Decision.ACT_AUTO
        and actual == Decision.ACT_AUTO
        and result.authorized
    ):
        useful_lead = state.decision_inputs.usable_lead_time_minutes

    return {
        "scenario_id": scenario["scenario_id"],
        "synthetic": bool(scenario["synthetic"]),
        "expected_decision": expected.value,
        "policy_decision": actual.value,
        "authorized": result.authorized,
        "reason_code": result.reason_code,
        "correct": correct,
        "false_action": false_action,
        "unnecessary_abstention": unnecessary_abstention,
        "unsafe_authorization": unsafe_authorization,
        "useful_lead_time_minutes": useful_lead,
    }


def evaluate_frozen_dataset() -> dict[str, Any]:
    scenarios = load_scenarios()
    policy = load_policy()

    rows = [evaluate_scenario(scenario, policy) for scenario in scenarios]

    total = len(rows)
    correct = sum(row["correct"] for row in rows)

    non_action_expected = sum(
        row["expected_decision"] not in {"ACT_AUTO", "ACT_HUMAN"}
        for row in rows
    )
    false_actions = sum(row["false_action"] for row in rows)

    non_abstain_expected = sum(
        row["expected_decision"] != "ABSTAIN"
        for row in rows
    )
    unnecessary_abstentions = sum(
        row["unnecessary_abstention"] for row in rows
    )

    unsafe_authorizations = sum(
        row["unsafe_authorization"] for row in rows
    )

    lead_times = [
        row["useful_lead_time_minutes"]
        for row in rows
        if row["useful_lead_time_minutes"] is not None
    ]

    metrics = {
        "scenario_count": total,
        "decision_accuracy": correct / total if total else 0.0,
        "false_action_count": false_actions,
        "false_action_rate": (
            false_actions / non_action_expected
            if non_action_expected else 0.0
        ),
        "unnecessary_abstention_count": unnecessary_abstentions,
        "unnecessary_abstention_rate": (
            unnecessary_abstentions / non_abstain_expected
            if non_abstain_expected else 0.0
        ),
        "unsafe_authorization_count": unsafe_authorizations,
        "unsafe_authorization_rate": (
            unsafe_authorizations / total if total else 0.0
        ),
        "mean_useful_lead_time_minutes": (
            sum(lead_times) / len(lead_times) if lead_times else None
        ),
        "minimum_useful_lead_time_minutes": (
            min(lead_times) if lead_times else None
        ),
    }

    passed = (
        metrics["decision_accuracy"] == 1.0
        and metrics["false_action_count"] == 0
        and metrics["unnecessary_abstention_count"] == 0
        and metrics["unsafe_authorization_count"] == 0
    )

    return {
        "evaluation_name": "cascade-breaker-gate4b-policy-quality",
        "dataset_type": "frozen-synthetic",
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "metrics": metrics,
        "pass": passed,
        "scenarios": rows,
    }


def main() -> int:
    report = evaluate_frozen_dataset()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_PATH.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    with DATASET_PATH.open("w", encoding="utf-8") as handle:
        for row in report["scenarios"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps(report, indent=2))
    print(f"REPORT: {REPORT_PATH}")
    print(f"DATASET: {DATASET_PATH}")

    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
