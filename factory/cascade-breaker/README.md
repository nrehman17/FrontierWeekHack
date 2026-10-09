# Cascade Breaker

**SME operational resilience through early-warning analysis, adversarial review, and a deterministic action gate.**

Cascade Breaker is a prototype for helping a small business recognize when several weak signals may combine into a supplier or operational disruption. It separates AI-generated analysis from action authority: the agents may recommend, challenge, or veto, but a deterministic policy gate controls the final decision.

> **Prototype boundary:** The Streamlit screen is a deterministic replay over synthetic scenarios. It does not connect to live SME inventory, suppliers, customers, or production systems. The demo intentionally marks critical evidence as incomplete, so it cannot authorize an operational action.

## What it demonstrates

1. **Scout** — surfaces weak signals from the selected scenario.
2. **Cascade** — forms a hypothesis about how those signals may develop and identifies a possible intervention window.
3. **Skeptic** — challenges the hypothesis and checks for false-positive patterns or missing evidence.
4. **Governor** — synthesizes the agent outputs into an advisory recommendation.
5. **Deterministic policy gate** — applies policy rules and evidence-completeness checks. The language-model agents do not have final action authority.

The runtime is designed to fail closed when critical evidence is incomplete. A high confidence score by itself is not enough to authorize an action.

## SME supplier-delay examples

The file `data/sme_supplier_delay_scenarios.json` contains three **synthetic** cases:

- **Early warning:** a revised delivery estimate could threaten a Friday customer order, leaving time to verify stock and contact the supplier.
- **Late warning:** a delay is reported close to the customer deadline, requiring immediate human review.
- **False alarm:** conflicting supplier messages must be reconciled before the warning is cleared.

All three cases remain `ABSTAIN` at runtime because their source records are unverified. Human approval is required before switching suppliers, placing consequential commitments, or promising a delivery date.

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

## Live Microsoft Foundry path

A separate live orchestration path is implemented in `src/live_orchestrator.py` and invokes the configured Foundry agents. It requires a correctly configured Foundry project endpoint, agent setup, Azure identity, and observability dependencies. The Streamlit replay does **not** invoke this path. Do not describe a live Foundry run as verified unless its invocation and trace evidence have been captured for the specific run.

## Current limitations and next validation steps

- Scenario inputs are synthetic; no real supplier, stock, or customer data is connected.
- Source provenance and independent evidence completeness are not yet verified by a live integration.
- The policy gate is tested with deterministic unit tests and synthetic fixtures; this is not proof of production readiness.
- Before any pilot, define authenticated source connectors, freshness and reconciliation rules, audit retention, human escalation ownership, and an explicit approval boundary for each consequential action.
- Measure false actions, unnecessary abstentions, decision accuracy, and useful lead time on a reviewed evaluation set before claiming operational impact.

## Repository locations

- `app.py` — Streamlit demo replay
- `src/agents.py` — deterministic demo agents
- `src/live_orchestrator.py` — Microsoft Foundry orchestration path
- `src/policy.py` — deterministic action policy
- `src/schemas.py` — validated decision and agent data models
- `data/scenarios.json` — core policy scenarios
- `data/sme_supplier_delay_scenarios.json` — synthetic SME supplier-delay cases
- `tests/` — policy and evaluation tests
