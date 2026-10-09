import json
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.agents import run_scout, run_cascade, run_skeptic, run_governor
from src.orchestrator import load_scenarios, build_decision_inputs
from src.policy import load_policy, evaluate_policy
from src.schemas import DecisionState, PolicyRef, Evidence, Agents

st.set_page_config(
    page_title="Cascade Breaker",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Cascade Breaker")
st.caption(
    "Predict the cascade. Challenge the hypothesis. "
    "Authorize only through a deterministic safety gate. "
    "This UI is a deterministic demo replay; live Microsoft Foundry agent execution is verified separately."
)

scenarios = load_scenarios()

# Separate SME-facing walkthrough uses its own synthetic dataset. It is
# explanatory only and does not feed unverified supplier data into policy.
SME_DATA_PATH = Path(__file__).resolve().parent / "data" / "sme_supplier_delay_scenarios.json"
sme_dataset = json.loads(SME_DATA_PATH.read_text(encoding="utf-8"))
sme_cases = sme_dataset["scenarios"]

with st.expander("SME supplier-delay walkthrough · synthetic case study", expanded=False):
    st.caption(
        "Illustrative small-manufacturer case. These records are synthetic and unverified; "
        "this walkthrough is separate from the policy replay and cannot authorize action."
    )
    sme_case_id = st.selectbox(
        "Choose supplier-delay situation",
        [case["scenario_id"] for case in sme_cases],
        format_func=lambda case_id: next(
            case["title"] for case in sme_cases if case["scenario_id"] == case_id
        ),
        key="sme_supplier_case",
    )
    sme_case = next(case for case in sme_cases if case["scenario_id"] == sme_case_id)

    st.markdown(f"**Risk hypothesis:** {sme_case['risk_hypothesis']}")
    st.markdown(f"**Review timing:** {sme_case['next_review_deadline']}")
    st.markdown("**Evidence to verify**")
    st.dataframe(
        [
            {
                "Source": item["source"],
                "Observed": item["observed_at"],
                "Claim": item["claim"],
                "Verified": "Yes" if item["verified"] else "No",
            }
            for item in sme_case["evidence"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    left_sme, right_sme = st.columns(2)
    with left_sme:
        st.markdown("**Counter-evidence to check**")
        for item in sme_case["counter_evidence_to_check"]:
            st.write(f"• {item}")
    with right_sme:
        st.markdown("**Human next steps**")
        for item in sme_dataset["shared_context"]["proposed_human_actions"]:
            st.write(f"• {item}")
    st.warning(
        "Runtime posture: ABSTAIN — reconcile evidence and route for human review. "
        "Do not switch suppliers or promise a delivery date without human approval."
    )


# Cross-domain critical-resource scenarios are a separate, advisory-only
# walkthrough. They never feed the policy replay or authorize operational action.
CRITICAL_DATA_PATH = Path(__file__).resolve().parent / "data" / "critical_resource_resilience_scenarios.json"
critical_dataset = json.loads(CRITICAL_DATA_PATH.read_text(encoding="utf-8"))
critical_cases = critical_dataset["scenarios"]

with st.expander("Critical-resource resilience · facilities, hospital oxygen, IPTV/OTT", expanded=False):
    st.caption(
        "Synthetic design walkthrough only. No live telemetry is connected; "
        "time-to-impact is intentionally not calculated and every case remains ABSTAIN."
    )
    critical_case_id = st.selectbox(
        "Choose critical-resource scenario",
        [case["scenario_id"] for case in critical_cases],
        format_func=lambda case_id: next(
            case["title"] for case in critical_cases if case["scenario_id"] == case_id
        ),
        key="critical_resource_case",
    )
    critical_case = next(
        case for case in critical_cases if case["scenario_id"] == critical_case_id
    )
    st.markdown(f"**Domain:** {critical_case['domain']}")
    st.markdown(f"**Trigger:** {critical_case['trigger']}")
    st.markdown(f"**Cascade hypothesis:** {critical_case['cascade_hypothesis']}")
    st.warning(
        f"Decision: {critical_case['decision']} — {critical_case['reason']}"
    )

    left_resource, right_resource = st.columns(2)
    with left_resource:
        st.markdown("**Illustrative observations — all unverified**")
        st.dataframe(
            [
                {
                    "Source": item["source"],
                    "Claim": item["claim"],
                    "Verified": "Yes" if item["verified"] else "No",
                }
                for item in critical_case["illustrative_observations"]
            ],
            hide_index=True,
            use_container_width=True,
        )
    with right_resource:
        st.markdown("**Counter-evidence to check**")
        for item in critical_case["counter_evidence_to_check"]:
            st.write(f"• {item}")
        st.markdown("**Recommended human response**")
        for item in critical_case["recommended_human_response"]:
            st.write(f"• {item}")

    st.info(
        "Time-to-impact: not calculated. Verify live measurements, timestamps, units, "
        "source provenance, equipment limits and recovery/replenishment estimates first. "
        "This walkthrough cannot authorize shutdowns, switching or clinical decisions."
    )

labels = {
    "S1_ACT": "🔥 Cost Cascade — intervention available",
    "S2_VETO": "🛑 Stable Straggler — false positive",
    "S3_ABSTAIN": "⚠️ Ambiguous Cost Drift — insufficient evidence",
}

selected_id = st.selectbox(
    "Choose scenario",
    [s["scenario_id"] for s in scenarios],
    format_func=lambda x: labels.get(x, x),
)

scenario = next(s for s in scenarios if s["scenario_id"] == selected_id)

mode = st.radio(
    "Execution mode",
    ["Deterministic demo replay", "Microsoft Foundry live"],
    horizontal=True,
    help="Live mode invokes four configured Microsoft Foundry agents. It does not connect live operational telemetry.",
)
live_confirmed = False
if mode == "Microsoft Foundry live":
    st.warning(
        "Live mode makes real Foundry model calls and may incur Azure/model charges. "
        "It uses the selected synthetic scenario; no infrastructure action is executed."
    )
    live_confirmed = st.checkbox(
        "I understand and approve running the four Foundry agents for this synthetic scenario.",
        key="confirm_foundry_run",
    )

if st.button("Run Cascade Analysis", type="primary", use_container_width=True):
    if mode == "Microsoft Foundry live":
        if not live_confirmed:
            st.error("Confirm the live Foundry run before any model calls are made.")
        else:
            try:
                from src.live_orchestrator import run_live_scenario
                with st.spinner("Calling the configured Microsoft Foundry agents…"):
                    live_record = run_live_scenario(scenario)
                st.subheader("Live Microsoft Foundry result")
                st.success("Foundry agents returned validated responses. The deterministic gate still has final authority.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Governor recommendation", live_record["governor_recommendation"])
                c2.metric("Deterministic decision", live_record["policy_decision"])
                c3.metric("Authorized", str(live_record["authorized"]))
                st.code(
                    f"Run ID: {live_record['run_id']}\n"
                    f"Scenario: {live_record['scenario_id']}\n"
                    f"Reason: {live_record['reason_code']}\n"
                    "Evidence complete: False\n"
                    "Missing evidence: independent_observations, validated_source_provenance"
                )
                live_agents = live_record["state"]["agents"]
                st.subheader("Foundry agent responses")
                for role in ("scout", "cascade", "skeptic", "governor"):
                    with st.expander(role.title(), expanded=(role == "governor")):
                        st.json(live_agents[role])
                with st.expander("Foundry invocation metadata and audit trace IDs"):
                    st.json(live_record["foundry_invocations"])
                st.info(
                    "This run used a synthetic scenario. No live telemetry was fetched, "
                    "and no operational action was executed. Evidence remains incomplete, "
                    "so the deterministic gate must fail closed."
                )
            except Exception as exc:
                # Never silently fall back to demo results in Live mode.
                st.error(
                    f"Live Foundry run failed ({type(exc).__name__}). "
                    "No demo result was substituted. Check FOUNDRY_ENDPOINT, Azure identity, "
                    "the four configured agent names, SDK versions, and deployment access."
                )
                st.caption("Sensitive exception details are intentionally not shown in the UI.")
    else:
        with st.spinner("Running deterministic demo agents…"):
            pass
        scout = run_scout(scenario)
        cascade = run_cascade(scenario, scout)
        skeptic = run_skeptic(scenario, cascade)
        governor = run_governor(scenario, scout, cascade, skeptic)

        policy = load_policy()
        inputs = build_decision_inputs(scenario)

        # The UI replay must use the same fail-closed evidence posture as the
        # runtime orchestrator. Synthetic fixtures are not verified evidence.
        state = DecisionState(
            run_id=str(uuid4()),
            scenario_id=scenario["scenario_id"],
            started_at=datetime.now(timezone.utc),
            policy=PolicyRef(
                policy_id=policy["policy_id"],
                policy_version=policy["policy_version"],
            ),
            evidence=Evidence(
                evidence_complete=False,
                missing_evidence=[
                    "independent_observations",
                    "validated_source_provenance",
                ],
            ),
            decision_inputs=inputs,
            agents=Agents(
                scout=scout,
                cascade=cascade,
                skeptic=skeptic,
                governor=governor,
            ),
        )

        result = evaluate_policy(state, policy)

        st.subheader("1 · Weak Signals")

        cols = st.columns(len(scenario["weak_signals"]))
        for col, signal in zip(cols, scenario["weak_signals"]):
            col.info(signal)

        st.subheader("2 · Forward Cascade")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Confidence", f"{inputs.confidence_p:.0%}")
        m2.metric("Predicted tipping point", f"{inputs.predicted_lead_minutes:.0f} min")
        m3.metric("Usable intervention window", f"{inputs.usable_lead_time_minutes:.0f} min")
        m4.metric("Action tier", inputs.action_tier.value)

        st.subheader("3 · Multi-Agent Reasoning")

        a, b, c, d = st.columns(4)

        with a:
            st.markdown("### 🔎 Scout")
            st.write(scout.reason)
            st.caption("Detect weak correlated signals")

        with b:
            st.markdown("### 🌊 Cascade")
            st.write(cascade.hypothesis)
            st.caption(f"Proposed: {cascade.proposed_action}")

        with c:
            st.markdown("### 🧪 Skeptic")
            st.write(f"Verdict: **{skeptic.verdict.value}**")
            st.write(skeptic.reason)
            st.caption("Can block — cannot authorize")

        with d:
            st.markdown("### 🏛️ Governor")
            st.write(
                f"Recommendation: **{governor.recommended_decision.value}**"
            )
            st.write(governor.reason)
            st.caption("Advisory only")

        st.subheader("4 · Cascade Action Gate")

        left, right = st.columns([2, 1])

        with left:
            st.markdown(
                """
                **Final authority is deterministic — not the LLM.**

                Policy evaluates confidence, intervention time,
                action tier, cost ratio and registered false-positive patterns.
                The current replay uses synthetic fixtures, so critical evidence
                is deliberately marked incomplete and cannot authorize an action.
                """
            )

            st.code(
                f"""Governor recommendation : {governor.recommended_decision.value}
    Deterministic decision   : {result.decision.value}
    Authorized               : {result.authorized}
    Reason                    : {result.reason_code}
    Evidence complete        : {state.evidence.evidence_complete}
    Missing evidence         : {", ".join(state.evidence.missing_evidence)}"""
            )

        with right:
            if result.decision.value == "ACT_AUTO":
                st.success("✅ ACT_AUTO")
            elif result.decision.value == "ACT_HUMAN":
                st.warning("👤 ACT_HUMAN")
            elif result.decision.value == "VETO":
                st.error("🛑 VETO")
            else:
                st.warning("⚠️ ABSTAIN")

            st.metric(
                "Usable lead time",
                f"{inputs.usable_lead_time_minutes:.0f} min",
            )

        st.subheader("5 · Evidence and Demo Limits")

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Scenarios in this demo", "3")
        e2.metric("Evidence independently verified", "No")
        e3.metric("Autonomous action authorized", "No")
        e4.metric("Live system integration", "Not enabled")

        st.caption(
            "All scenarios in this replay are synthetic. The UI does not connect "
            "to live infrastructure or independently verify source provenance. "
            "Prior evaluation scores, if any, are not recomputed by this replay."
        )

    else:
        st.info("Choose a scenario and press **Run Cascade Analysis**.")
