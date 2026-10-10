"""FIN-DOM dashboard entry point (Person B).

Step 1: skeleton only. Page config, session state, sidebar, KPI cards, four tabs.
The source list below is a TEMPORARY placeholder; it will be replaced by
mock data in the next step and later by the real engine.
"""
import streamlit as st

st.set_page_config(
    page_title="FIN-DOM | Financial Domino Effect",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- TEMPORARY placeholder (synthetic names, not engine data) ----
PLACEHOLDER_SOURCES = ["Meridian Bank", "Harbor Insurance", "Atlas Fund"]

# ---- Session state: defaults set once per browser session ----
DEFAULTS = {
    "selected_source": PLACEHOLDER_SOURCES[0],
    "severity": 70,
    "result": None,  # holds the scenario result after Run
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def reset_scenario():
    """Callback: restore defaults and clear any result."""
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


# ---- Sidebar ----
with st.sidebar:
    st.title("🕸️ FIN-DOM")
    st.caption("Financial Domino Effect simulator (synthetic data)")
    st.divider()
    st.selectbox("Source institution", PLACEHOLDER_SOURCES, key="selected_source")
    st.slider("Shock severity (%)", 0, 100, key="severity")
    run_clicked = st.button("▶ Run", type="primary", use_container_width=True)
    st.button("Reset", on_click=reset_scenario, use_container_width=True)

if run_clicked:
    # Placeholder: the real/mock cascade gets wired in a later step.
    st.session_state["result"] = {"placeholder": True}

# ---- Header and KPI cards ----
st.title("Financial Domino Effect")
st.caption("Pick a source institution, set a severity, and click Run.")

has_result = st.session_state["result"] is not None
kpis = [("Entities hit", "—"), ("Failed entities", "—"), ("Total loss", "—"), ("Rounds", "—")]
for col, (label, value) in zip(st.columns(4), kpis):
    col.metric(label, value)

if has_result:
    st.info(
        f"Scenario stored: **{st.session_state['selected_source']}** at "
        f"**{st.session_state['severity']}%** severity. Results will appear here once wired."
    )
else:
    st.info("No scenario run yet.")

# ---- Tabs ----
tab_network, tab_ranking, tab_explain, tab_about = st.tabs(
    ["Network", "Ranking", "Explain", "About / Method"]
)
with tab_network:
    st.write("Network graph goes here.")
with tab_ranking:
    st.write("Baseline vs scenario ranking goes here.")
with tab_explain:
    st.write("Explanation panel goes here.")
with tab_about:
    st.write("Method and limitations go here.")
