from src.evaluation import evaluate_frozen_dataset


def test_frozen_policy_quality_evaluation_passes():
    report = evaluate_frozen_dataset()
    metrics = report["metrics"]

    assert report["pass"] is True
    assert metrics["scenario_count"] == 3
    assert metrics["decision_accuracy"] == 1.0
    assert metrics["false_action_count"] == 0
    assert metrics["false_action_rate"] == 0.0
    assert metrics["unnecessary_abstention_count"] == 0
    assert metrics["unnecessary_abstention_rate"] == 0.0
    assert metrics["unsafe_authorization_count"] == 0
    assert metrics["unsafe_authorization_rate"] == 0.0
    assert metrics["mean_useful_lead_time_minutes"] == 90.0
    assert metrics["minimum_useful_lead_time_minutes"] == 90.0

    by_id = {row["scenario_id"]: row for row in report["scenarios"]}

    assert by_id["S1_ACT"]["policy_decision"] == "ACT_AUTO"
    assert by_id["S1_ACT"]["authorized"] is True

    assert by_id["S2_VETO"]["policy_decision"] == "VETO"
    assert by_id["S2_VETO"]["authorized"] is False

    assert by_id["S3_ABSTAIN"]["policy_decision"] == "ABSTAIN"
    assert by_id["S3_ABSTAIN"]["authorized"] is False



def test_synthetic_scenarios_define_separate_runtime_expectations():
    from src.orchestrator import load_scenarios

    scenarios = {item["scenario_id"]: item for item in load_scenarios()}

    assert scenarios["S1_ACT"]["expected_decision"] == "ACT_AUTO"
    assert scenarios["S1_ACT"]["expected_runtime_decision"] == "ABSTAIN"
    assert scenarios["S2_VETO"]["expected_runtime_decision"] == "VETO"
    assert scenarios["S3_ABSTAIN"]["expected_runtime_decision"] == "ABSTAIN"
    assert all(item["synthetic"] is True for item in scenarios.values())



def test_sme_supplier_delay_fixtures_fail_closed_on_unverified_evidence():
    import json
    from pathlib import Path

    fixture_path = Path(__file__).resolve().parents[1] / "data" / "sme_supplier_delay_scenarios.json"
    dataset = json.loads(fixture_path.read_text(encoding="utf-8"))
    scenarios = dataset["scenarios"]

    assert dataset["dataset_type"] == "synthetic"
    assert {item["variant"] for item in scenarios} == {
        "early_warning", "late_warning", "false_alarm"
    }
    assert all(item["synthetic"] is True for item in scenarios)
    assert all(item["expected_runtime_decision"] == "ABSTAIN" for item in scenarios)
    assert all(
        evidence["verified"] is False
        for item in scenarios
        for evidence in item["evidence"]
    )
    assert any(
        "Human approval required before switching suppliers" in constraint
        for constraint in dataset["shared_context"]["approval_constraints"]
    )
