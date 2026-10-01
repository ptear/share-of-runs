"""Interactive renderings: plotly, altair, bokeh.

Same chart as the static versions. Each library gets one page per colouring,
with a season selector covering the five seasons plus the combined view, so
each page carries six panels' worth of views.

Script sources are pinned to hosts that work both on GitHub Pages and inside a
published artifact: plotly from cdnjs, vega/vega-lite from jsdelivr, bokeh inlined.
"""
import os
import pandas as pd
from chart_common import (load, cuts, limits, legend_for, HIGHLIGHT, SEASONS, MODES,
                          SURFACE, INK, INK_SOFT, GRID, FIELD)

OUT = "site/charts"
os.makedirs(OUT, exist_ok=True)

D = load()
XC, YC = cuts(D)
XL, YL = limits(D)
PANELS = ["2022–2026"] + [str(y) for y in SEASONS]
BOTH = pd.concat([D.assign(panel=D.season.astype(str)),
                  D.assign(panel="2022–2026")], ignore_index=True)
SYMBOL = {"Opener": "circle", "Middle order": "square", "All-rounder / keeper": "triangle-up"}
QUAD = [(XL[1], YL[1], "Good by both", "right", "top"),
        (XL[1], YL[0], "Flattered by average", "right", "bottom"),
        (XL[0], YL[1], "Undervalued by average", "left", "top"),
        (XL[0], YL[0], "Poor by both", "left", "bottom")]
PLOTLY_CDN = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/3.0.1/plotly.min.js"
TITLE = "Batting average against median % of match runs — Division 1 specialist batters"
HOVER_COLS = ["player", "season", "teams", "role", "innings", "runs",
              "high_score_disp", "pct_team_runs", "top_scorer_rate", "composite_pctl",
              "strike_rate", "bdry_pct", "rotate"]


def groups(mode):
    """Legend order for the mode; the grey 'rest' group goes first so it sits behind."""
    lg = legend_for(mode, D)
    return (["Other batters"] + list(lg)) if mode == "performers" else list(lg)


def colour_for(mode, group):
    lg = legend_for(mode, D)
    return lg.get(group, FIELD)


# ---------------------------------------------------------------- plotly
def plotly_chart(mode):
    import plotly.graph_objects as go
    fig = go.Figure()
    order = groups(mode)
    for panel in PANELS:
        p = BOTH[BOTH.panel == panel]
        for grp in order:
            s = p[p[f"group_{mode}"] == grp]
            big = not (mode == "performers" and grp == "Other batters")
            fig.add_trace(go.Scatter(
                x=s.average, y=s.med_pct_match,
                mode="markers+text" if (mode == "performers" and big) else "markers",
                name=grp, legendgroup=grp, visible=(panel == "2022–2026"),
                text=s.label if (mode == "performers" and big) else None,
                textposition="middle right",
                textfont=dict(size=10, color=colour_for(mode, grp)),
                marker=dict(size=12 if big else 7, color=colour_for(mode, grp),
                            line=dict(width=1.2 if big else 0,
                                      color=INK if (mode != "performers" and
                                                    len(s) and s.player.isin(HIGHLIGHT).all())
                                      else SURFACE),
                            symbol=[SYMBOL[r] for r in s.role]),
                customdata=s[HOVER_COLS].values,
                hovertemplate=(
                    "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<br><br>"
                    "average <b>%{x:.1f}</b> · median %% of match runs <b>%{y:.2f}%</b><br>"
                    "%{customdata[4]} inns · %{customdata[5]} runs · HS %{customdata[6]}<br>"
                    "%{customdata[7]:.1f}%% of team runs · top scorer %{customdata[8]:.0f}%% "
                    "of inns<br>SR %{customdata[10]:.1f} · boundary %{customdata[11]:.1f}%% · "
                    "rotate %{customdata[12]:.1f}<br>composite %{customdata[9]:.1f}"
                    "<extra></extra>")))
    per = len(order)
    buttons = []
    for i, panel in enumerate(PANELS):
        vis = [False] * (len(PANELS) * per)
        for j in range(per):
            vis[i * per + j] = True
        buttons.append(dict(label=panel, method="update", args=[{"visible": vis}]))
    fig.update_layout(
        template="simple_white", height=660, margin=dict(l=70, r=30, t=100, b=70),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        title=dict(text=f"{TITLE}<br><span style='font-size:12px;color:{INK_SOFT}'>"
                        f"coloured by {MODES[mode]}</span>",
                   x=0, xanchor="left", font=dict(size=16, color=INK)),
        xaxis=dict(title="batting average", range=list(XL), gridcolor=GRID),
        yaxis=dict(title="median % of match runs", range=list(YL), gridcolor=GRID),
        shapes=[dict(type="line", x0=XC, x1=XC, y0=YL[0], y1=YL[1],
                     line=dict(color=GRID, width=1)),
                dict(type="line", x0=XL[0], x1=XL[1], y0=YC, y1=YC,
                     line=dict(color=GRID, width=1))],
        annotations=[dict(x=x, y=y, text=f"<i>{t}</i>", showarrow=False, xanchor=xa,
                          yanchor=ya, font=dict(size=11, color=INK_SOFT))
                     for x, y, t, xa, ya in QUAD],
        legend=dict(orientation="h", y=-0.14, x=0, font=dict(size=11)),
        updatemenus=[dict(buttons=buttons, direction="right", x=0, y=1.07, xanchor="left",
                          yanchor="bottom", showactive=True, bgcolor="#ffffff",
                          bordercolor=GRID, font=dict(size=11), pad=dict(t=2, b=2))])
    fig.write_html(f"{OUT}/plotly_{mode}.html", include_plotlyjs=PLOTLY_CDN, full_html=True,
                   config={"displaylogo": False,
                           "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


# ---------------------------------------------------------------- altair
def altair_chart(mode):
    import altair as alt
    alt.data_transformers.disable_max_rows()
    src = D.copy()
    lg = legend_for(mode, D)
    domain = list(lg) if mode != "performers" else list(lg) + ["Other batters"]
    rng = [lg[k] for k in lg] + ([FIELD] if mode == "performers" else [])
    sel = alt.selection_point(
        fields=["season"], bind=alt.binding_select(
            options=[None] + SEASONS,
            labels=["2022–2026 (all)"] + [str(y) for y in SEASONS], name="season  "),
        value=None)
    leg = alt.selection_point(fields=[f"group_{mode}"], bind="legend")
    base = (alt.Chart(src).add_params(sel, leg).transform_filter(sel))
    enc = dict(
        x=alt.X("average:Q", title="batting average", scale=alt.Scale(domain=list(XL))),
        y=alt.Y("med_pct_match:Q", title="median % of match runs",
                scale=alt.Scale(domain=list(YL))),
        shape=alt.Shape("role:N", title="position", scale=alt.Scale(
            domain=list(SYMBOL), range=["circle", "square", "triangle-up"])),
        color=alt.Color(f"group_{mode}:N", title="",
                        scale=alt.Scale(domain=domain, range=rng),
                        legend=alt.Legend(columns=3 if mode == "team" else 1, symbolLimit=20)),
        opacity=alt.condition(leg, alt.value(.95), alt.value(.12)),
        size=alt.condition(alt.FieldOneOfPredicate("player", list(HIGHLIGHT)),
                           alt.value(170), alt.value(48)),
        tooltip=[alt.Tooltip("player:N", title="player"),
                 alt.Tooltip("season:O", title="season"),
                 alt.Tooltip("teams:N", title="county"),
                 alt.Tooltip("role:N", title="position"),
                 alt.Tooltip("innings:Q", title="innings"),
                 alt.Tooltip("runs:Q", title="runs"),
                 alt.Tooltip("average:Q", title="average", format=".1f"),
                 alt.Tooltip("med_pct_match:Q", title="median % match runs", format=".2f"),
                 alt.Tooltip("pct_team_runs:Q", title="% of team runs", format=".1f"),
                 alt.Tooltip("top_scorer_rate:Q", title="top scorer %", format=".0f"),
                 alt.Tooltip("strike_rate:Q", title="strike rate", format=".1f"),
                 alt.Tooltip("bdry_pct:Q", title="boundary %", format=".1f"),
                 alt.Tooltip("rotate:Q", title="rotate (runs/100 non-bdry balls)",
                             format=".1f"),
                 alt.Tooltip("composite_pctl:Q", title="composite", format=".1f")])
    pts = base.mark_point(filled=True, stroke=SURFACE, strokeWidth=1).encode(**enc)
    labels = (base.transform_filter(alt.FieldOneOfPredicate("player", list(HIGHLIGHT)))
              .mark_text(align="left", dx=11, dy=-3, fontSize=10, fontWeight="bold")
              .encode(x="average:Q", y="med_pct_match:Q", text="label:N",
                      color=alt.Color(f"group_{mode}:N", legend=None,
                                      scale=alt.Scale(domain=domain, range=rng))))
    vline = alt.Chart(pd.DataFrame({"x": [XC]})).mark_rule(color=GRID).encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [YC]})).mark_rule(color=GRID).encode(y="y:Q")
    quads = [alt.Chart(pd.DataFrame({"x": [x], "y": [y], "t": [t]})).mark_text(
        align=xa, baseline=ya, fontStyle="italic", fontSize=11, color=INK_SOFT,
        dx=6 if xa == "left" else -6, dy=8 if ya == "top" else -8).encode(
        x="x:Q", y="y:Q", text="t:N") for x, y, t, xa, ya in QUAD]
    chart = (alt.layer(vline, hline, *quads, pts, labels)
             .properties(width=800, height=520,
                         title=alt.TitleParams(TITLE, subtitle=f"coloured by {MODES[mode]}",
                                               anchor="start", fontSize=15, color=INK,
                                               subtitleColor=INK_SOFT))
             .configure_view(fill=SURFACE, stroke=None)
             .configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID,
                             labelColor=INK_SOFT, titleColor=INK_SOFT))
    chart.save(f"{OUT}/altair_{mode}.html")


# ---------------------------------------------------------------- bokeh
def bokeh_chart(mode):
    from bokeh.plotting import figure, save, output_file
    from bokeh.models import (ColumnDataSource, HoverTool, Span, Label, CustomJS, Select)
    from bokeh.layouts import column
    from bokeh.resources import INLINE

    output_file(f"{OUT}/bokeh_{mode}.html", title="Average vs share of match runs")
    p = figure(width=880, height=560, background_fill_color=SURFACE,
               border_fill_color=SURFACE, x_range=XL, y_range=YL,
               tools="pan,wheel_zoom,box_zoom,reset,save", title=TITLE)
    p.title.text_font_size = "14px"; p.title.text_color = INK
    p.xaxis.axis_label = "batting average"; p.yaxis.axis_label = "median % of match runs"
    p.grid.grid_line_color = GRID; p.outline_line_color = None
    p.axis.axis_line_color = GRID; p.axis.major_tick_line_color = GRID
    p.axis.axis_label_text_color = INK_SOFT; p.axis.major_label_text_color = INK_SOFT
    p.add_layout(Span(location=XC, dimension="height", line_color=GRID, line_width=1))
    p.add_layout(Span(location=YC, dimension="width", line_color=GRID, line_width=1))
    for x, y, t, xa, ya in QUAD:
        p.add_layout(Label(x=x, y=y, text=t, text_font_size="10px", text_color=INK_SOFT,
                           text_font_style="italic", text_align=xa,
                           text_baseline="top" if ya == "top" else "bottom",
                           y_offset=-6 if ya == "top" else 6,
                           x_offset=-6 if xa == "right" else 6))
    pairs = []
    for grp in groups(mode):
        for role, mk in [("Opener", "circle"), ("Middle order", "square"),
                         ("All-rounder / keeper", "triangle")]:
            sub = BOTH[(BOTH[f"group_{mode}"] == grp) & (BOTH.role == role)]
            if sub.empty:
                continue
            big = not (mode == "performers" and grp == "Other batters")
            full = ColumnDataSource(sub)
            view = ColumnDataSource(sub[sub.panel == "2022–2026"])
            p.scatter("average", "med_pct_match", source=view, marker=mk,
                      size=13 if big else 7, fill_color=colour_for(mode, grp),
                      line_color=SURFACE if big else None, line_width=1.2 if big else 0,
                      fill_alpha=.95, legend_label=grp)
            pairs.append({"full": full, "view": view})
    p.legend.orientation = "horizontal"; p.legend.location = "top_left"
    p.legend.label_text_font_size = "10px"; p.legend.click_policy = "hide"
    p.legend.background_fill_color = SURFACE; p.legend.border_line_color = None
    p.add_layout(p.legend[0], "below")
    p.add_tools(HoverTool(tooltips="""
        <div style="font:12px system-ui;padding:3px 5px">
          <div style="font-weight:700">@player · @season</div>
          <div style="color:#52514e">@teams · @role</div>
          <div style="margin-top:4px">average <b>@average{0.0}</b> ·
            median % match runs <b>@med_pct_match{0.00}%</b></div>
          <div>@innings inns · @runs runs · HS @high_score_disp</div>
          <div>@pct_team_runs{0.0}% of team runs · top scorer @top_scorer_rate{0}% of inns</div>
          <div>SR @strike_rate{0.0} · boundary @bdry_pct{0.0}% · rotate @rotate{0.0}</div>
          <div>composite @composite_pctl{0.0}</div>
        </div>"""))
    sel = Select(title="Season", value="2022–2026", options=PANELS, width=200)
    sel.js_on_change("value", CustomJS(args=dict(pairs=pairs), code="""
        const want = cb_obj.value;
        for (const {full, view} of pairs) {
          const src = full.data, keys = Object.keys(src), out = {};
          for (const k of keys) out[k] = [];
          for (let i = 0; i < src['panel'].length; i++) {
            if (src['panel'][i] === want) for (const k of keys) out[k].push(src[k][i]);
          }
          view.data = out;
        }"""))
    save(column(sel, p), resources=INLINE)


if __name__ == "__main__":
    for mode in MODES:
        plotly_chart(mode); altair_chart(mode); bokeh_chart(mode)
        print(f"{mode}: plotly + altair + bokeh ok")
