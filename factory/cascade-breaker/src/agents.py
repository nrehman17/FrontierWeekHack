from __future__ import annotations

from typing import Any

from src.schemas import (
    AgentStatus,
    CascadeState,
    Decision,
    GovernorState,
    ScoutState,
    SkepticState,
    SkepticVerdict,
)


def run_scout(scenario: dict[str, Any]) -> ScoutState:
    """Detect weak multi-signal evidence. Scout has no action authority."""
    return ScoutState(
        status=AgentStatus.COMPLETE,
        weak_signals=list(scenario["weak_signals"]),
        confidence=float(scenario["confidence_p"]),
        reason="Synthetic telemetry contains the weak signals supplied for this demo scenario.",
    )


def run_cascade(
    scenario: dict[str, Any],
    scout: ScoutState,
) -> CascadeState:
    """Construct the cascade hypothesis and proposed intervention."""
    tipping_point = float(scenario["predicted_lead_minutes"])

    return CascadeState(
        status=AgentStatus.COMPLETE,
        hypothesis=(
            f"{scenario['title']}: correlated weak signals may form a forward cascade."
        ),
        tipping_point_minutes=tipping_point,
        proposed_action=scenario["proposed_action"],
        confidence=float(scenario["confidence_p"]),
        reason=(
            "Cascade hypothesis constructed from Scout evidence; "
            "this recommendation does not authorize execution."
        ),
    )


def run_skeptic(
    scenario: dict[str, Any],
    cascade: CascadeState,
) -> SkepticState:
    """Adversarially challenge the cascade hypothesis and intervention."""
    verdict = SkepticVerdict(scenario["skeptic_verdict"])
    false_positive = scenario.get("false_positive_pattern")

    contradictory_evidence: list[str] = []
    missing_evidence: list[str] = []

    if verdict == SkepticVerdict.CONTRADICT:
        contradictory_evidence.append(
            "Observed evidence matches a known stable-pattern alternative."
        )
    elif verdict == SkepticVerdict.INSUFFICIENT:
        missing_evidence.append(
            "Additional correlated evidence is required before intervention."
        )

    return SkepticState(
        status=AgentStatus.COMPLETE,
        verdict=verdict,
        false_positive_pattern=false_positive,
        alternative_hypothesis=(
            "Observed behavior may be steady-state or non-causal."
            if verdict == SkepticVerdict.CONTRADICT
            else None
        ),
        contradictory_evidence=contradictory_evidence,
        missing_evidence=missing_evidence,
        reason=(
            "Skeptic independently challenges the proposed cascade; "
            "it may block but cannot authorize action."
        ),
    )


def run_governor(
    scenario: dict[str, Any],
    scout: ScoutState,
    cascade: CascadeState,
    skeptic: SkepticState,
) -> GovernorState:
    """Synthesize agent evidence. Governor recommends; policy code decides."""
    if skeptic.false_positive_pattern or skeptic.verdict == SkepticVerdict.CONTRADICT:
        recommendation = Decision.VETO
    elif skeptic.verdict == SkepticVerdict.INSUFFICIENT:
        recommendation = Decision.ABSTAIN
    elif float(scenario["confidence_p"]) >= 0.8:
        recommendation = Decision.ACT_AUTO
    elif float(scenario["confidence_p"]) >= 0.6:
        recommendation = Decision.ACT_HUMAN
    else:
        recommendation = Decision.ABSTAIN

    return GovernorState(
        status=AgentStatus.COMPLETE,
        recommended_decision=recommendation,
        confidence=float(scenario["confidence_p"]),
        reason=(
            "Governor synthesized Scout, Cascade, and Skeptic outputs. "
            "Recommendation is advisory; deterministic policy retains authority."
        ),
    )
