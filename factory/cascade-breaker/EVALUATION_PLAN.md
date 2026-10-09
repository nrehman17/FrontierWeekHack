# Cascade Breaker Evaluation Plan

**Status:** planned evaluation work; not evidence of production readiness.  
**Current baseline:** a small synthetic scenario set and deterministic policy tests. The live Microsoft Foundry path must be reported separately from deterministic demo replay.

## 1. Decision semantics

- **VETO** — a deterministic blocking rule has fired. The action is prohibited for this evaluation, regardless of a high model confidence or Governor recommendation. Record the specific blocking reason.
- **ABSTAIN** — the system cannot justify an authorized action because evidence is incomplete, confidence is in an abstention band, or one or more intervention criteria are unmet. Route for review or request additional evidence.
- **ACTHUMAN** — policy criteria support a recommendation that requires an authorized human decision. This is not execution authorization.
- **ACTAUTO** — policy thresholds permit a bounded action only where that action class has been explicitly approved by policy. It must never be inferred from the Governor's recommendation alone.

The deterministic policy gate—not a language-model agent—must assign the final state. In reporting, distinguish a policy VETO from an agent's skeptical disagreement; disagreement is input to the gate, not automatically a VETO unless a configured deterministic rule matches it.

## 2. Evaluation layers

Keep results separate so a successful layer cannot be mistaken for proof of another:

1. **Deterministic policy tests:** threshold edges, missing required inputs, evidence completeness, prohibited tiers, veto precedence, cost ratio, lead-time margin, and unauthorized agent recommendations.
2. **Agent contract tests:** valid schema, malformed JSON, wrong JSON type, missing/extra fields, null values, unexpected enum values, and truncated output.
3. **Orchestration and dependency tests:** unavailable agent, timeout, throttling, authentication failure, partial run, tracing failure, and retry exhaustion. A failed run must not produce an authorized action or silently fall back to demo output.
4. **Adversarial tests:** scenario text containing instructions to ignore policy, fabricated provenance, contradictory timestamps, stale observations presented as current, and attempts by an agent to claim it has authority.
5. **Dataset evaluation:** a versioned, independently reviewed set of labeled incidents, non-incidents, ambiguous cases, and near-threshold cases. Keep a held-out test set separate from prompt and threshold tuning.

## 3. Minimum test matrix

| Area | Example variations | Required invariant |
|---|---|---|
| Threshold edges | Just below, exactly at, and just above every confidence, lead-time, and cost-ratio threshold | Result follows documented boundary semantics exactly |
| Evidence quality | Missing source, unverified source, stale observation, conflicting timestamps, incomplete independent observations | No automatic action while required evidence is incomplete |
| Agent output | Invalid JSON, schema mismatch, null or wrong-type fields, unexpected enum | Run fails safely; no default permissive values |
| Agent disagreement | Scout supports, Cascade uncertain, Skeptic contradicts, Governor recommends ACT | Governor cannot override policy; disagreement is visible and auditable |
| Prompt injection | Scenario/evidence text asks agent to ignore rules or disclose secrets | Treat input as data; policy and authorization boundary remain intact |
| Dependency failure | Agent unavailable, timeout, rate limit, credential error, tracing outage | No silent demo substitution and no authorization from a partial run |
| Policy boundary | Prohibited action tier, registered veto pattern, missing required input, evidence incomplete | Deterministic precedence and reason codes are stable |
| Replay integrity | Repeat same fixture and policy version | Deterministic layer yields the same result; model outputs are separately recorded as variable |

For each test, record the fixture ID, dataset version, policy version, schema version, expected outcome, observed outcome, pass/fail, and evidence link. Do not count repeated variations of one synthetic fixture as independent real-world incidents.

## 4. Metrics and reporting

Publish denominators, confidence intervals where appropriate, dataset composition, and the decision threshold used. Do not report a metric if its ground-truth labels or denominator are unavailable.

- **Precision:** true positive incident detections / all positive incident detections.
- **Recall:** true positive incident detections / all labeled incidents.
- **Calibration:** compare predicted probabilities with observed event frequencies, using a reliability plot and a proper scoring rule where the dataset supports it. A model confidence field is not automatically a calibrated probability.
- **False-action rate:** unauthorized or policy-disallowed action decisions / all evaluated cases, with a separate count of any ACTAUTO result on a labeled unsafe case. Target zero for policy-invariant tests; report observed performance without implying a finite test proves zero risk.
- **Abstention rate:** ABSTAIN results / all evaluated cases, reported alongside missed incidents and review workload.
- **Latency:** end-to-end and per-agent latency, including failures and retries; report percentiles rather than only the mean.
- **Cost:** model/API cost per run and per correctly detected incident, with model/deployment and token assumptions recorded.
- **Useful lead time:** verified time between first actionable alert and incident onset, only for incidents with trustworthy timestamps.
- **Veto rate and reasons:** report deterministic vetoes separately from abstentions and agent disagreement.

Do not set production thresholds from the same dataset used to claim performance. Use a labeled development set for tuning and a held-out set for final reporting.

## 5. Reproducibility appendix

For each evaluation release, retain:

- Agent names and immutable/versioned identifiers; model and deployment identifiers where available.
- System/developer prompts and prompt hashes, with a short change log explaining each iteration.
- Pydantic/schema versions and validation behavior.
- Policy file version/hash, thresholds, action-tier definitions, veto precedence, and change approval.
- Dataset version, fixture IDs, label definitions, inclusion/exclusion rules, and known limitations.
- Run IDs, timestamps, per-agent status, latency, token/cost metadata when available, and trace links with sensitive data removed.
- Failed experiments and regressions, including the reason for rejection; never report only successful runs.

Avoid putting credentials, personal data, sensitive incident details, or secrets into prompts, logs, or the appendix.

## 6. Shadow-mode pilot before any action enablement

1. Obtain written approval from the operational owner and safety/security reviewers; define the scope and stop conditions.
2. Use historical incidents first. Reconstruct only information that was available at each historical timestamp to avoid hindsight leakage.
3. Run in shadow mode on a read-only, approved feed. Cascade Breaker may emit recommendations and alerts but must not call action tools or change operational state.
4. Have qualified reviewers label incidents, non-incidents, missed detections, false alarms, and whether the proposed lead time was useful.
5. Review false positives, missed incidents, abstention burden, evidence provenance, latency, cost, and all policy-boundary failures.
6. Require a documented go/no-go review and a rollback plan before any bounded action is considered. Any later automation must be limited to explicitly approved low-risk actions with independent monitoring and a kill switch.

For clinical, life-safety, infrastructure, or other high-consequence settings, this prototype's synthetic evaluation is not a basis for autonomous action.

## 7. Current limitations

The current synthetic fixtures and deterministic tests validate selected software invariants; they do not establish field accuracy, calibrated confidence, operational usefulness, or production readiness. The Microsoft Foundry live path and the deterministic demo replay are distinct execution modes and must be described and measured separately. No live operational telemetry or real-world shadow-mode results should be claimed until they have actually been collected and reviewed.
