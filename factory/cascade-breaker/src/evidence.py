from math import isfinite
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AIClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_p: float = Field(ge=0.0, le=1.0)
    predicted_lead_minutes: float = Field(ge=0.0)
    evidence_ids: list[str] = Field(min_length=1)

    @field_validator("confidence_p", "predicted_lead_minutes")
    @classmethod
    def finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("value must be finite")
        return value


def validate_ai_claim(claim: AIClaim, evidence_ids: set[str]) -> AIClaim:
    missing = set(claim.evidence_ids) - evidence_ids
    if missing:
        raise ValueError(
            f"AI claim references unknown evidence: {sorted(missing)}"
        )
    return claim


def validate_evidence_integrity(
    *,
    trusted_evidence: dict[str, object],
    ai_evidence: dict[str, object],
) -> None:
    for evidence_id, trusted_value in trusted_evidence.items():
        if evidence_id in ai_evidence and ai_evidence[evidence_id] != trusted_value:
            raise ValueError(
                f"AI attempted to overwrite trusted evidence: {evidence_id}"
            )
