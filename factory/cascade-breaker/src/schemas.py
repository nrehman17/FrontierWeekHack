from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Decision(str, Enum):
    ACT_AUTO = "ACT_AUTO"
    ACT_HUMAN = "ACT_HUMAN"
    ABSTAIN = "ABSTAIN"
    VETO = "VETO"


class ActionTier(str, Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class AgentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class SkepticVerdict(str, Enum):
    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    INSUFFICIENT = "INSUFFICIENT"


class PolicyRef(StrictModel):
    policy_id: str
    policy_version: str


class EvidenceItem(StrictModel):
    evidence_id: str
    timestamp: datetime
    source: str
    metric: str
    value: float
    baseline: Optional[float] = None
    change_pct: Optional[float] = None
    cohort: Optional[str] = None
    synthetic: bool = True


class Evidence(StrictModel):
    observations: list[EvidenceItem] = Field(default_factory=list)
    secondary_evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence_complete: bool = False


class DecisionInputs(StrictModel):
    confidence_p: Optional[float] = Field(None, ge=0, le=1)
    predicted_lead_minutes: Optional[float] = Field(None, ge=0)
    action_latency_minutes: Optional[float] = Field(None, ge=0)
    safety_margin_minutes: Optional[float] = Field(None, ge=0)
    usable_lead_time_minutes: Optional[float] = None
    action_tier: Optional[ActionTier] = None
    false_action_cost_cf: Optional[float] = Field(None, ge=0)
    inaction_cost_ci: Optional[float] = Field(None, gt=0)
    cf_ci_ratio: Optional[float] = Field(None, ge=0)


class ScoutState(StrictModel):
    status: AgentStatus = AgentStatus.PENDING
    weak_signals: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    reason: Optional[str] = None


class CascadeState(StrictModel):
    status: AgentStatus = AgentStatus.PENDING
    hypothesis: Optional[str] = None
    tipping_point_minutes: Optional[float] = Field(None, ge=0)
    proposed_action: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    reason: Optional[str] = None


class SkepticState(StrictModel):
    status: AgentStatus = AgentStatus.PENDING
    verdict: Optional[SkepticVerdict] = None
    false_positive_pattern: Optional[str] = None
    alternative_hypothesis: Optional[str] = None
    contradictory_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class GovernorState(StrictModel):
    status: AgentStatus = AgentStatus.PENDING
    recommended_decision: Optional[Decision] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    reason: Optional[str] = None


class Agents(StrictModel):
    scout: ScoutState = Field(default_factory=ScoutState)
    cascade: CascadeState = Field(default_factory=CascadeState)
    skeptic: SkepticState = Field(default_factory=SkepticState)
    governor: GovernorState = Field(default_factory=GovernorState)


class GateState(StrictModel):
    decision: Optional[Decision] = None
    authorized: bool = False
    reason_code: Optional[str] = None


class AbstainState(StrictModel):
    active: bool = False
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    ttl_minutes: Optional[float] = Field(None, ge=0)
    last_call_required: bool = False


class DecisionState(StrictModel):
    schema_version: str = "1.0"
    run_id: str
    scenario_id: str
    scenario_version: str = "1.0"
    started_at: datetime
    policy: PolicyRef
    evidence: Evidence
    decision_inputs: DecisionInputs
    agents: Agents = Field(default_factory=Agents)
    gate: GateState = Field(default_factory=GateState)
    abstain: AbstainState = Field(default_factory=AbstainState)
    final_decision: Optional[Decision] = None
    completed_at: Optional[datetime] = None
