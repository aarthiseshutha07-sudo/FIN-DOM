"""Ranking tab: baseline vs scenario risk scores (Person B).

Takes plain DataFrames/dicts and does not import the mock or the engine.
Field names follow the CURRENT mock structures and live in the constants below.
"""
import pandas as pd
import streamlit as st
from app import layout


# ---- Names of the fields this view reads (adapt here when real structures land) ----
ID, NAME, TYPE = "id", "name", "type"
BASE_ID, BASE_SCORE = "id", "baseline_score"
SCENARIO_SCORES, STATUS, SOURCE_ID = "scenario_score", "status", "source_id"

STATUS_ICONS = {"Stable": "🟢 Stable", "Stressed": "🟠 Stressed", "Failed": "🔴 Failed"}


def build_table(entities, baseline, result=None):
    """Return the display table. Without a result: baseline only."""
    df = entities[[ID, NAME, TYPE]].merge(
        baseline[[BASE_ID, BASE_SCORE]], left_on=ID, right_on=BASE_ID, how="left"
    )
    df = df.rename(columns={NAME: "Institution", TYPE: "Type", BASE_SCORE: "Baseline"})

    if result is None:
        df = df.sort_values("Baseline", ascending=False)
        df.insert(0, "Rank", range(1, len(df) + 1))
        return df[["Rank", "Institution", "Type", "Baseline"]]

    df["Scenario"] = df[ID].map(result[SCENARIO_SCORES])
    df["Change"] = (df["Scenario"] - df["Baseline"]).round(1)
    df["Status"] = df[ID].map(result[STATUS]).map(STATUS_ICONS)
    df = df.sort_values("Scenario", ascending=False)
    df.insert(0, "Rank", range(1, len(df) + 1))
    df["Institution"] = [
        f"★ {n}" if i == result[SOURCE_ID] else n for i, n in zip(df[ID], df["Institution"])
    ]
    return df[["Rank", "Institution", "Type", "Baseline", "Scenario", "Change", "Status"]]


def to_csv_bytes(table, result=None):
    """CSV for download: plain text only (no icons or star), plus an 'Is source' flag."""
    out = table.copy()
    is_source = out["Institution"].str.startswith("★ ")
    out["Institution"] = out["Institution"].str.replace("★ ", "", regex=False)
    if result is not None:
        out["Status"] = out["Status"].str.split(" ", n=1).str[-1]
        out["Is source"] = is_source
    return out.to_csv(index=False).encode("utf-8")

def render(entities, baseline, result):
    """Draw the Ranking tab content."""
    table = build_table(entities, baseline, result)

    score = st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f")
    config = {
        "Rank": st.column_config.NumberColumn(width="small"),
        "Baseline": score,
    }
    if result is None:
        st.caption("Baseline risk score (0-100) for every institution. "
                   "Run a scenario to compare against it.")
    else:
        config["Scenario"] = score
        config["Change"] = st.column_config.NumberColumn(format="%+.1f")
        worst = table.iloc[0]
        st.caption(f"Ranked by scenario score. ★ = source. Highest scenario risk: "
                   f"**{worst['Institution'].lstrip('★ ')}** ({worst['Scenario']:.1f}). "
                   "Click a column header to sort.")

        st.dataframe(table, hide_index=True, column_config=config,
                 height=min(35 * (len(table) + 1) + 3, 900), **layout.stretch(st.dataframe))
        
        name = "fin-dom_baseline.csv" if result is None else (
            f"fin-dom_scenario_{result[SOURCE_ID]}_{result.get('severity', 0)}pct.csv")
        st.download_button("⬇ Download as CSV", data=to_csv_bytes(table, result),
                        file_name=name, mime="text/csv")