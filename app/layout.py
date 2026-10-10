"""Shared page layout: page setup, styling, sidebar, header, KPI cards (Person B).

Pure UI. It knows nothing about the mock or the engine; values are passed in.
"""
import inspect

import streamlit as st

# Full-width widgets: newer Streamlit uses width="stretch", older uses use_container_width.
# Use as: st.button("Run", **STRETCH)
if "width" in inspect.signature(st.button).parameters:
    STRETCH = {"width": "stretch"}
else:
    STRETCH = {"use_container_width": True}

# Theme-aware (semi-transparent) so it works in both light and dark mode.
_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1400px; }
[data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.10);
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 12px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricLabel"] { opacity: 0.8; }
@media (max-width: 640px) {
    .block-container { padding-left: 0.8rem; padding-right: 0.8rem; padding-top: 1rem; }
    h1 { font-size: 1.6rem !important; }
}
</style>
"""


def configure_page():
    """Must be the first Streamlit call in the app."""
    st.set_page_config(
        page_title="FIN-DOM | Financial Domino Effect",
        page_icon="🕸️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def render_sidebar(source_ids, names, on_run, on_reset):
    """Sidebar controls. Widget values live in st.session_state under the keys below."""
    with st.sidebar:
        st.title("🕸️ FIN-DOM")
        st.caption("Financial Domino Effect simulator (synthetic data)")
        st.divider()
        st.selectbox("Source institution", source_ids,
                     format_func=lambda i: names[i], key="selected_source")
        st.slider("Shock severity (%)", 0, 100, key="severity")
        st.button("▶ Run", type="primary", on_click=on_run, **STRETCH)
        st.button("Reset", on_click=on_reset, **STRETCH)


def render_header():
    st.title("Financial Domino Effect")
    st.caption("Pick a source institution, set a severity, and click Run.")


def render_kpis(kpis):
    """kpis: dict with hit, failed, loss, rounds; or None before the first run."""
    if kpis is None:
        values = ["—"] * 4
    else:
        values = [kpis["hit"], kpis["failed"], f"{kpis['loss']:,.0f}M", kpis["rounds"]]
    labels = ["Entities hit", "Failed entities", "Total loss", "Rounds"]
    for col, label, value in zip(st.columns(4), labels, values):
        col.metric(label, value)


def render_status(source_name, severity):
    """Banner under the KPI cards. Pass source_name=None before the first run."""
    if source_name is None:
        st.info("No scenario run yet. Choose a source institution and click Run.")
    else:
        st.success(f"Scenario: **{source_name}** shocked at **{severity}%** severity. "
                   "(Mock data, illustrative only.)")