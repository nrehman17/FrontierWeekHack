# Cascade Breaker

**Operational resilience through early-warning analysis, adversarial review, and a deterministic action gate.**

Cascade Breaker is a prototype for recognizing when weak signals combine into a supplier or operational disruption. It separates AI-generated analysis from action authority: agents may recommend, challenge, or veto, but a deterministic policy gate controls the final decision.

> **Prototype boundary:** The Streamlit screen is a deterministic replay over synthetic scenarios. It does not connect to live infrastructure, suppliers, hospitals, or production systems. Critical evidence is deliberately incomplete, so the demo cannot authorize consequential actions.

## What it demonstrates

1. **Scout** — surfaces weak signals from a scenario.
2. **Cascade** — forms a hypothesis about how signals may develop and identifies a possible intervention window.
3. **Skeptic** — challenges the hypothesis and checks for false positives or missing evidence.
4. **Governor** — synthesizes agent outputs into an advisory recommendation.
5. **Deterministic policy gate** — applies policy rules and evidence-completeness checks. Language-model agents do not have final action authority.

The runtime is designed to fail closed when critical evidence is incomplete. A high confidence score by itself is not enough to authorize an action. The Skeptic must explicitly return `SUPPORT` for policy evaluation to continue; `CONTRADICT`, `INSUFFICIENT`, or a missing verdict leads to `ABSTAIN`. A registered false-positive pattern can trigger a configured deterministic `VETO`. Low confidence maps to `ABSTAIN`, because uncertainty is not itself a policy prohibition. Cost ratios are recomputed from source cost inputs and inconsistent values fail closed.

## SME supplier-delay examples

The file `data/sme_supplier_delay_scenarios.json` contains three **synthetic** cases: early warning, late warning, and a false alarm. The records remain `ABSTAIN` at runtime because their source records are unverified. Human approval is required before switching suppliers or making consequential customer commitments.

## Cross-domain critical-resource resilience

The files `data/critical_resource_resilience_scenarios.json` and `CRITICAL_RESOURCE_RESILIENCE.md` extend the design to three synthetic cases:

- **IT park / critical facilities:** extended grid outage, diesel shortage, UPS/generator endurance, and dependencies such as server rooms, cooling, networking and life-safety systems.
- **Hospital oxygen supply:** changing demand and uncertain replenishment, with clinical decisions reserved for authorised clinical teams.
- **Broadcast / IPTV / OTT:** storm risk correlated with feed telemetry, headend dependencies and potential downstream service impact.

These are design fixtures, not live telemetry or validated forecasts. The time-to-impact fields are intentionally unset until real, fresh, verified evidence and an approved calculation method exist. The scenarios fail closed. They do not authorize shutdowns, switching, medical allocation, patient ranking or treatment withdrawal.

## Run the demo locally

Use Python 3.12 or a compatible supported Python 3 version.

```bash
cd factory/cascade-breaker
python -m venv .venv
```

Activate the virtual environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install demo dependencies and start Streamlit:

```bash
python -m pip install -r requirements-demo.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, choose a scenario, and select **Run Cascade Analysis**.

## Run the tests

From `factory/cascade-breaker`:

```bash
python -m pip install pytest
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m src.orchestrator
```

The GitHub Actions workflow runs these checks on relevant pushes and pull requests.

## Live Microsoft Foundry mode

The Streamlit UI now offers **Deterministic demo replay** and **Microsoft Foundry live** modes. Demo replay remains the default. Live mode requires a separate checkbox confirmation before it makes four real Foundry model calls. If a live call fails, the UI shows an error and does not fall back to demo output.

Live mode still uses a **synthetic scenario**, not live operational telemetry. It does not connect to supplier systems, weather feeds, power/fuel sensors, hospital systems or broadcast telemetry. The deterministic policy gate remains the final authority and the fixture's evidence is deliberately incomplete, so the expected posture is `ABSTAIN`.

Install the optional live dependencies from this directory:

```bash
python -m pip install -r requirements-live.txt
```

Configure the Foundry project endpoint in the environment variable `FOUNDRY_ENDPOINT` (the project endpoint URL, not a model deployment URL). Sign in with an Azure identity supported by `DefaultAzureCredential`, for example with `az login`, and ensure that identity has permission to use the Foundry project. The following four versioned agents must already exist in the project:

- `cascade-breaker-scout`
- `cascade-breaker-cascade`
- `cascade-breaker-skeptic`
- `cascade-breaker-governor`

Then launch `streamlit run app.py`, select **Microsoft Foundry live**, review the charge warning, and explicitly confirm the run. Four model invocations can incur charges according to your Azure deployment and pricing. Do not enable unattended live calls.

If `CASCADE_BREAKER_TRACE=1` is set, configure the Foundry project's linked Application Insights connection and the optional tracing dependency; otherwise tracing is a no-op. Do not describe a live Foundry run as verified unless its invocation metadata and, when enabled, trace evidence have been captured for that run.

## Current limitations and validation steps

- Scenario inputs are synthetic; no live inventory, weather, power, fuel, oxygen, broadcast or customer data is connected.
- Source provenance and independent evidence completeness are not yet verified by live integration.
- Deterministic tests on synthetic fixtures are not proof of production readiness.
- Before a pilot, define authenticated source connectors, freshness and reconciliation rules, audit retention, human escalation ownership, and explicit approval boundaries.
- Measure false actions, unnecessary abstentions, decision accuracy, and useful lead time on a reviewed evaluation set before claiming operational impact.
- The test and live-evaluation roadmap is documented in [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md). It defines decision semantics, adversarial and failure-mode test categories, metric definitions, reproducibility artifacts, and a proposed shadow-mode pilot; it does not claim those evaluations have already been completed. Recovery and post-action verification requirements are documented in [`RECOVERY_WORKFLOW.md`](RECOVERY_WORKFLOW.md); execution, independent verification, and rollback are not implemented.

## Repository locations

- `app.py` — Streamlit demo replay
- `src/agents.py` — deterministic demo agents
- `src/live_orchestrator.py` — Microsoft Foundry orchestration path
- `src/policy.py` — deterministic action policy
- `src/schemas.py` — validated decision and agent data models
- `data/scenarios.json` — core policy scenarios
- `data/sme_supplier_delay_scenarios.json` — synthetic SME supplier-delay cases
- `data/critical_resource_resilience_scenarios.json` — synthetic cross-domain resource-risk cases
- `CRITICAL_RESOURCE_RESILIENCE.md` — model and safety boundary for cross-domain cases
- `EVALUATION_PLAN.md` — planned benchmark, metric definitions, failure-mode coverage and shadow-mode gate
- `RECOVERY_WORKFLOW.md` — proposed post-action verification and recovery design; not implemented
- `tests/` — policy and evaluation tests
