import json
from pathlib import Path

from src.orchestrator import run_scenario


def test_local_synthetic_run_marks_evidence_incomplete():
    scenarios = json.loads(
        (Path(__file__).parents[1] / "data" / "scenarios.json").read_text()
    )
    scenario = next(
        scenario
        for scenario in scenarios["scenarios"]
        if scenario["scenario_id"] == "S1_ACT"
    )

    record = run_scenario(scenario)
    evidence = record["state"]["evidence"]

    assert evidence["evidence_complete"] is False
    assert evidence["missing_evidence"] == ["independent_observations"]
