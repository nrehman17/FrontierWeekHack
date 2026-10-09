import json
from pathlib import Path


def test_critical_resource_scenarios_are_synthetic_and_fail_closed():
    path = Path(__file__).resolve().parents[1] / "data" / "critical_resource_resilience_scenarios.json"
    dataset = json.loads(path.read_text(encoding="utf-8"))

    assert dataset["dataset_type"] == "synthetic"
    assert dataset["safety_boundary"]["live_data_connected"] is False
    assert dataset["safety_boundary"]["autonomous_actions_permitted"] is False
    assert dataset["safety_boundary"]["clinical_triage_or_patient_allocation"] is False

    scenarios = dataset["scenarios"]
    assert {item["scenario_id"] for item in scenarios} == {
        "FACILITY_DIESEL_CONSTRAINT",
        "HOSPITAL_OXYGEN_REPLENISHMENT_RISK",
        "HEADEND_STORM_SIGNAL_RISK",
    }
    assert all(item["synthetic"] is True for item in scenarios)
    assert all(item["decision"] == "ABSTAIN" for item in scenarios)
    assert all(item["time_to_impact"]["value"] is None for item in scenarios)

    hospital = next(item for item in scenarios if item["domain"] == "Hospital critical supply")
    assert any("clinical triage" in item.lower() for item in hospital["reason"].split(";") + [hospital["reason"]])
