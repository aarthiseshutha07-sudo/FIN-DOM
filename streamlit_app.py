"""FIN-DOM dashboard entry point (Person B).

Step 3: Run button wired to the mock cascade; KPI cards show real (mock) numbers.
All data access goes through the DATA ACCESS section below, so swapping the mock
for Person A's engine later means editing only that section.
"""
import streamlit as st

# ======================= DATA ACCESS (swap point) =======================
# TEMPORARY: mock data. Replace these imports/functions when the real engine
# structures are known. Nothing below this section touches mock_data directly.
from app import mock_data
from app import network_view



@st.cache_data
def get_data():
    """Return (entities, exposures). Cached so it loads once."""
    return mock_data.mock_load_data()


@st.cache_data
def get_baseline():
    entities, exposures = get_data()
    return mock_data.mock_baseline(entities, exposures)


def run_scenario(source_id, severity_pct):
    entities, exposures = get_data()
    return mock_data.mock_cascade(entities, exposures, source_id, severity_pct)


def compute_kpis(result):
    """Turn a result into the four KPI values shown on the dashboard."""
    statuses = result["status"].values()
    return {
        "hit": sum(s != "Stable" for s in statuses),
        "failed": sum(s == "Failed" for s in statuses),
        "loss": result["total_loss"],
        "rounds": result["rounds"],
    }
# ========================================================================

st.set_page_config(
    page_title="FIN-DOM | Financial Domino Effect",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

entities, exposures = get_data()
names = entities.set_index("id")["name"].to_dict()
source_ids = list(names)

# ---- Session state: defaults set once per browser session ----
DEFAULTS = {
    "selected_source": source_ids[0],
    "severity": 70,
    "result": None,  # scenario result after Run
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def reset_scenario():
    """Callback: restore defaults and clear any result."""
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def on_run():
    """Callback: run the scenario and store it in session state."""
    st.session_state["result"] = run_scenario(
        st.session_state["selected_source"], st.session_state["severity"]
    )


# ---- Sidebar ----
with st.sidebar:
    st.title("🕸️ FIN-DOM")
    st.caption("Financial Domino Effect simulator (synthetic data)")
    st.divider()
    st.selectbox(
        "Source institution", source_ids,
        format_func=lambda i: names[i], key="selected_source",
    )
    st.slider("Shock severity (%)", 0, 100, key="severity")
    st.button("▶ Run", type="primary", on_click=on_run, use_container_width=True)
    st.button("Reset", on_click=reset_scenario, use_container_width=True)

# ---- Header and KPI cards ----
st.title("Financial Domino Effect")
st.caption("Pick a source institution, set a severity, and click Run.")

result = st.session_state["result"]
if result is None:
    values = {"hit": "—", "failed": "—", "loss": "—", "rounds": "—"}
else:
    k = compute_kpis(result)
    values = {"hit": k["hit"], "failed": k["failed"],
              "loss": f"{k['loss']:,.0f}M", "rounds": k["rounds"]}

cards = [("Entities hit", values["hit"]), ("Failed entities", values["failed"]),
         ("Total loss", values["loss"]), ("Rounds", values["rounds"])]
for col, (label, value) in zip(st.columns(4), cards):
    col.metric(label, value)

if result is None:
    st.info("No scenario run yet.")
else:
    st.success(
        f"Scenario: **{names[result['source_id']]}** shocked at "
        f"**{result['severity']}%** severity. (Mock data, illustrative only.)"
    )

# ---- Tabs ----
tab_network, tab_ranking, tab_explain, tab_about = st.tabs(
    ["Network", "Ranking", "Explain", "About / Method"]
)
with tab_network:
     network_view.render(entities, exposures, st.session_state["result"])
with tab_ranking:
    st.write("Baseline vs scenario ranking goes here.")
with tab_explain:
    st.write("Explanation panel goes here.")
with tab_about:
    st.write("Method and limitations go here.")