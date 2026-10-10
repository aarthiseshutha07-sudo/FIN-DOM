"""Explain tab: why was the selected institution affected? (Person B)

Takes plain DataFrames/dicts plus an `explain_fn` callable; it never imports the
mock or the engine. Field names follow the CURRENT mock structures and live in
the constants below so they can be adapted in one place.
"""
import pandas as pd
import streamlit as st

# ---- Names of the fields this view reads (adapt here when real structures land) ----
ID, NAME, TYPE, REGION = "id", "name", "type", "region"
BASE_ID, BASE_SCORE = "id", "baseline_score"
SCENARIO_SCORES, STATUS, SOURCE_ID = "scenario_score", "status", "source_id"
STRESS_HISTORY, SEVERITY = "stress_history", "severity"
BEFORE, AFTER, REASONS = "stress_before", "stress_after", "reasons"  # keys of explain_fn's result

STATUS_ICONS = {"Stable": "🟢", "Stressed": "🟠", "Failed": "🔴"}


def render(entities, baseline, result, explain_fn):
    """Draw the Explain tab. `explain_fn(result, entity_id)` returns the explanation dict."""
    if result is None:
        st.session_state.pop("_explain_sig", None)  # so the next run picks a fresh default
        st.info("Run a scenario first, then pick an institution here to see why it was affected.")
        return

    names = entities.set_index(ID)[NAME].to_dict()
    final = result[STRESS_HISTORY][-1]
    ordered = sorted(names, key=lambda i: -final[i])  # most stressed first

    # New scenario -> default to the most affected institution; otherwise keep the choice.
    sig = (result[SOURCE_ID], result.get(SEVERITY), result.get("rounds"))
    if st.session_state.get("_explain_sig") != sig:
        st.session_state["_explain_sig"] = sig
        others = [i for i in ordered if i != result[SOURCE_ID]]
        # Default to the most affected institution other than the source (its story is richer).
        st.session_state["selected_entity"] = others[0] if others else ordered[0]

    def label(i):
        tag = " (source)" if i == result[SOURCE_ID] else ""
        return f"{STATUS_ICONS[result[STATUS][i]]} {names[i]}{tag}"

    entity_id = st.selectbox("Institution to explain", ordered, format_func=label,
                             key="selected_entity",
                             help="Sorted from most to least stressed.")

    info = explain_fn(result, entity_id)
    row = entities.set_index(ID).loc[entity_id]
    status = result[STATUS][entity_id]
    base = baseline.set_index(BASE_ID)[BASE_SCORE][entity_id]
    scen = result[SCENARIO_SCORES][entity_id]

    st.subheader(f"{names[entity_id]}  {STATUS_ICONS[status]} {status}")
    st.caption(f"{row[TYPE]} · {row[REGION]} region")

    c1, c2, c3 = st.columns(3)
    c1.metric("Stress (after run)", f"{info[AFTER]:.2f}",
              delta=f"{info[AFTER] - info[BEFORE]:+.2f} vs start", delta_color="inverse")
    c2.metric("Risk score", f"{scen:.1f}", delta=f"{scen - base:+.1f} vs baseline",
              delta_color="inverse")
    c3.metric("Baseline score", f"{base:.1f}")

    st.markdown("#### Why was it affected?")
    for reason in info[REASONS]:
        st.markdown(f"- {reason}")

    st.markdown("#### Stress by round")
    trend = pd.DataFrame(
        {"Stress": [step[entity_id] for step in result[STRESS_HISTORY]]},
        index=pd.Index(range(len(result[STRESS_HISTORY])), name="Round"),
    )
    st.line_chart(trend, height=220)
    st.caption("Stable < 0.25 · Stressed 0.25 to 0.99 · Failed ≥ 1.00 "
               "(mock data, illustrative only).")