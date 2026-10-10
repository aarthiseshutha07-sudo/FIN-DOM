"""Network tab: interactive Plotly graph with fixed node positions (Person B).

Takes plain DataFrames/dicts and does not import the mock or the engine.
Column and key names used here follow the CURRENT mock structures and are
collected in the constants below so they can be adapted in one place.
"""
import networkx as nx
import plotly.graph_objects as go
import streamlit as st
from app import layout


# ---- Names of the fields this view reads (adapt here when real structures land) ----
ID, NAME, TYPE, REGION, ASSETS = "id", "name", "type", "region", "assets"
EDGE_FROM, EDGE_TO, EDGE_AMOUNT = "from_id", "to_id", "amount"
STRESS_HISTORY, EVENTS, SOURCE_ID, ROUNDS = "stress_history", "events", "source_id", "rounds"

# ---- Visual settings ----
STATUS_COLORS = {"Stable": "#2e9d5b", "Stressed": "#f5a524", "Failed": "#e5484d"}
EDGE_COLOR = "rgba(140,140,140,0.30)"
HIT_EDGE_COLOR = "rgba(229,72,77,0.85)"
SOURCE_COLOR = "#7c5cff"  # halo + label color that marks the shocked institution


def status_from_stress(stress):
    """Label thresholds from the MVP spec (Stable <0.25, Stressed <1, Failed >=1)."""
    if stress >= 1.0:
        return "Failed"
    return "Stressed" if stress >= 0.25 else "Stable"


@st.cache_data
def _positions(node_ids, edges):
    """Fixed layout: same seed + same graph = same positions on every run."""
    g = nx.Graph()
    g.add_nodes_from(node_ids)
    g.add_edges_from(edges)
    return nx.spring_layout(g, seed=42, k=0.9)


def _edge_trace(pairs, pos, color, width, name=None):
    xs, ys = [], []
    for a, b in pairs:
        xs += [pos[a][0], pos[b][0], None]
        ys += [pos[a][1], pos[b][1], None]
    return go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=width),
                      hoverinfo="skip", name=name or "", showlegend=name is not None)


def build_figure(entities, exposures, result=None, view_round=0):
    ids = tuple(entities[ID])
    edges = tuple(zip(exposures[EDGE_FROM], exposures[EDGE_TO]))
    pos = _positions(ids, edges)

    # Node size by importance: total exposure touching the node.
    weight = {i: 0.0 for i in ids}
    for r in exposures.itertuples():
        weight[getattr(r, EDGE_FROM)] += getattr(r, EDGE_AMOUNT)
        weight[getattr(r, EDGE_TO)] += getattr(r, EDGE_AMOUNT)
    top = max(weight.values()) or 1

    stress = result[STRESS_HISTORY][view_round] if result else {i: 0.0 for i in ids}
    source = result[SOURCE_ID] if result else None

    fig = go.Figure()
    fig.add_trace(_edge_trace(edges, pos, EDGE_COLOR, 1))

    if result:
        hit = {(e["from_id"], e["to_id"]) for e in result[EVENTS] if e["round"] <= view_round}
        if hit:
            fig.add_trace(_edge_trace(hit, pos, HIT_EDGE_COLOR, 3, name="Loss path"))

    rows = entities.set_index(ID)

    def hover_data(i, status):
        return [rows.at[i, NAME], rows.at[i, TYPE], rows.at[i, REGION],
                rows.at[i, ASSETS], stress[i], status]

    hover = ("<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}"
             "<br>Assets: %{customdata[3]:,}M"
             "<br>Stress: %{customdata[4]:.2f} (%{customdata[5]})<extra></extra>")

    for status, color in STATUS_COLORS.items():
        members = [i for i in ids if i != source and status_from_stress(stress[i]) == status]
        fig.add_trace(go.Scatter(
            x=[pos[i][0] for i in members], y=[pos[i][1] for i in members],
            mode="markers", name=status,
            marker=dict(color=color, size=[14 + 22 * weight[i] / top for i in members],
                        line=dict(width=1, color="white")),
            customdata=[hover_data(i, status) for i in members], hovertemplate=hover,
        ))

    if source is not None:
        x, y = pos[source]
        size = 14 + 22 * weight[source] / top
        status = status_from_stress(stress[source])
        # Halo ring behind the node so the source stands out whatever its status color is.
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers", name="Source (shocked)", hoverinfo="skip",
            marker=dict(size=size + 26, color="rgba(124,92,255,0.25)",
                        line=dict(width=3, color=SOURCE_COLOR)),
        ))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", showlegend=False,
            text=[f"<b>SOURCE: {rows.at[source, NAME]}</b>"], textposition="top center",
            textfont=dict(color=SOURCE_COLOR, size=13),
            marker=dict(symbol="star", size=size + 8, color=STATUS_COLORS[status],
                        line=dict(width=2, color="white")),
            customdata=[hover_data(source, status)], hovertemplate=hover,
        ))

    fig.update_layout(
        height=620, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        legend=dict(orientation="h", y=1.04, x=0), hovermode="closest",
    )
    return fig, stress


def render(entities, exposures, result):
    """Draw the Network tab content."""
    view_round = 0
    if result:
        total = result[ROUNDS]
        # New scenario -> jump to the final round; keep the user's choice otherwise.
        sig = (result[SOURCE_ID], result.get("severity"), total)
        if st.session_state.get("_net_sig") != sig:
            st.session_state["_net_sig"] = sig
            st.session_state["view_round"] = total
        st.session_state["view_round"] = min(st.session_state.get("view_round", total), total)
        if total > 0:
            view_round = st.slider("Round", 0, total, key="view_round",
                                   help="Step through the contagion round by round.")
        else:
            st.caption("No spread: nothing was affected beyond the source.")

    fig, stress = build_figure(entities, exposures, result, view_round)
    st.plotly_chart(fig, **layout.stretch(st.plotly_chart))

    if result:
        labels = [status_from_stress(v) for v in stress.values()]
        st.caption(f"Round {view_round} of {result[ROUNDS]}: "
                   f"{labels.count('Stressed')} stressed, {labels.count('Failed')} failed. "
                   "Purple ring + star = source. Node size = total exposure. Red lines = loss paths.")
    else:
        st.caption("Run a scenario to see the contagion. Node size = total exposure. "
                   "Positions stay fixed between runs.")