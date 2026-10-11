"""FIN-DOM dashboard entry point (Person B).

Wires together data access, session state, and the layout and tab views.
All data access goes through the DATA ACCESS section below, so swapping the mock
for Person A's engine later means editing only that section.
"""
import streamlit as st

from app import about_view, explain_view, layout, network_view, ranking_view

layout.configure_page()  # must come before any other Streamlit output

# ======================= DATA ACCESS (swap point) =======================
# TEMPORARY: mock data. Replace these imports/functions when the real engine
# structures are known. Nothing below this section touches mock_data directly.
from app import mock_data


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


def explain_entity(result, entity_id):
    """Return the explanation dict for one institution."""
    entities, _ = get_data()
    return mock_data.mock_explain(result, entities, entity_id)


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


# ---- Page ----
layout.render_sidebar(source_ids, names, on_run, reset_scenario)
layout.render_header()

result = st.session_state["result"]
layout.render_kpis(compute_kpis(result) if result else None)
layout.render_status(names[result["source_id"]] if result else None,
                     result["severity"] if result else None)

tab_network, tab_ranking, tab_explain, tab_about = st.tabs(
    ["Network", "Ranking", "Explain", "About / Method"]
)
with tab_network:
    network_view.render(entities, exposures, result)
with tab_ranking:
    ranking_view.render(entities, get_baseline(), result)
with tab_explain:
    explain_view.render(entities, get_baseline(), result, explain_entity)
with tab_about:
    about_view.render()