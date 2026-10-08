import pytest

from src.evidence import (
    AIClaim,
    validate_ai_claim,
    validate_evidence_integrity,
)


def test_ai_cannot_overwrite_independent_evidence():
    trusted = {"inventory_001": 42}
    malicious = {"inventory_001": 999}

    with pytest.raises(ValueError, match="overwrite trusted evidence"):
        validate_evidence_integrity(
            trusted_evidence=trusted,
            ai_evidence=malicious,
        )


def test_ai_claim_must_reference_known_evidence():
    claim = AIClaim(
        confidence_p=0.99,
        predicted_lead_minutes=120,
        evidence_ids=["fabricated_001"],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_ai_claim(claim, {"inventory_001"})


def test_valid_ai_claim_can_pass_without_becoming_authoritative_evidence():
    claim = AIClaim(
        confidence_p=0.83,
        predicted_lead_minutes=120,
        evidence_ids=["inventory_001"],
    )

    validated = validate_ai_claim(claim, {"inventory_001"})

    assert validated.confidence_p == 0.83
    assert validated.predicted_lead_minutes == 120
