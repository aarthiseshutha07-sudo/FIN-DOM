"""About / Method tab: what FIN-DOM does, how the rules work, and its limits (Person B).

Static content taken from the MVP specification. It does not depend on the mock or the engine.
If the formulas or thresholds change in the engine, update the text here to match.
"""
import pandas as pd
import streamlit as st

# Flip to False once the UI runs on Person A's real engine and data.
USING_MOCK_DATA = True

CLAIMS = pd.DataFrame(
    [
        ("Graph of interconnected entities", "Yes", "Network of 25 synthetic entities"),
        ("Risk scoring and ranking", "Yes (formula-based)", "Rule-based risk score"),
        ("Scenario simulation", "Yes", "Deterministic cascade simulator"),
        ("Explainability", "Yes (rule-derived)", "Explanations traced from the propagation rules"),
        ("GNN", "No", "Planned future work"),
        ("Causal inference", "No", "Planned future work"),
        ("Real-time multi-source data", "No", "Uses static sample data; live feeds are future work"),
        ("Knowledge graph", "Partial", "Graph data model, not a full knowledge graph"),
    ],
    columns=["Vision component", "In this prototype?", "What we say"],
)


def render():
    """Draw the About / Method tab."""
    st.header("About FIN-DOM")
    st.write(
        "FIN-DOM shows a network of financial institutions, lets you shock one of them, "
        "and shows how losses spread through the network, which institutions are hit, and why. "
        "It is a **transparent, rule-based contagion simulator running on synthetic sample data**, "
        "not a forecasting model."
    )
    if USING_MOCK_DATA:
        st.warning(
            "This build is running on **temporary mock data** while the final engine is "
            "integrated. All names, numbers, and results are fictional and illustrative only."
        )

    st.subheader("What is and isn't implemented")
    st.table(CLAIMS.set_index("Vision component"))

    left, right = st.columns(2)
    with left:
        st.subheader("How the cascade works")
        st.markdown(
            "1. **Shock:** the source institution takes a hit equal to the severity times a "
            "fraction of its capital buffer. This gives it a stress level from 0 to 1, "
            "where 1 means its buffer is wiped out and it fails.\n"
            "2. **Propagate:** each round, every institution computes the losses from its "
            "stressed counterparties: *exposure × their stress × loss rate* (for example 60%). "
            "Dividing that loss by its own capital buffer gives its new stress level.\n"
            "3. **Repeat** until nothing changes, or after at most 10 rounds.\n"
            "4. **Label** each institution by its stress level."
        )
        st.markdown(
            "| Status | Stress level |\n|---|---|\n"
            "| 🟢 Stable | below 0.25 |\n"
            "| 🟠 Stressed | 0.25 to 0.99 |\n"
            "| 🔴 Failed | 1.0 or higher |"
        )
    with right:
        st.subheader("Baseline risk score (0-100)")
        st.markdown(
            "A weighted blend of three things:\n"
            "- **Leverage:** more debt means riskier.\n"
            "- **Capital cushion:** a thinner buffer means riskier.\n"
            "- **Interconnectedness:** more and larger links mean more exposure to "
            "others' problems."
        )
        st.subheader("Explainability")
        st.write(
            "Every loss can be traced to a specific link in a specific round, so each "
            "explanation is a plain sentence such as *\"lost 400M from exposure to "
            "Meridian Bank in round 1\"*. Nothing is a black box."
        )

    st.subheader("How to read the dashboard")
    st.markdown(
        "- **Node colour** shows status; **node size** shows total exposure.\n"
        "- A **purple ring and star** marks the shocked source institution.\n"
        "- **Red lines** show loss paths up to the round selected on the slider.\n"
        "- Node positions stay fixed between runs, so you can compare scenarios."
    )

    st.subheader("Limitations")
    st.markdown(
        "- All institutions and exposures are **fictional**; no real company data is used.\n"
        "- The simulator is **deterministic**: the same inputs always give the same result. "
        "It does not output probabilities or forecasts.\n"
        "- There are no trained machine-learning models and no live data feeds.\n"
        "- The rules are deliberately simple so every number can be explained; real "
        "financial systems are far more complex.\n"
        "- This tool is a prototype for demonstration, **not financial advice**."
    )