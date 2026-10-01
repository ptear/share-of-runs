"""Figure 2, re-cut — Division 1 rank by median % of match runs — in six libraries.

Rank 1 at the top, log scale, one line per player. Seasons where a player did not
reach the 12-innings qualification are gaps, not interpolated.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from chart_common import (HIGHLIGHT, SEASONS, SURFACE, INK, INK_SOFT, GRID)

OUT = "site/charts"
os.makedirs(OUT, exist_ok=True)
MIN_INNINGS = 12
TICKS = [1, 2, 5, 10, 25, 50, 100]
TITLE = "Division 1 rank by median % of match runs, by season"
SUB = ("rank 1 is best; a gap means the player did not reach "
       f"{MIN_INNINGS} innings that season")


def ranked():
    s = pd.read_csv("player_rankings_div1_by_season.csv")
    out = []
    for yr in SEASONS:
        g = s[(s.season == yr) & (s.innings >= MIN_INNINGS)].copy()
        g["rk"] = g.median_pct_match_runs.rank(ascending=False, method="min")
        g["pool"] = len(g)
        out.append(g)
    a = pd.concat(out)
    a = a[a.player.isin(HIGHLIGHT)].copy()
    a["name"] = a.player.map(lambda p: HIGHLIGHT[p][0])
    a["colour"] = a.player.map(lambda p: HIGHLIGHT[p][1])
    return a.sort_values(["name", "season"])[
        ["season", "player", "name", "colour", "teams", "role", "innings", "runs",
         "average", "high_score_disp", "median_pct_match_runs", "share_team_runs",
         "top_scorer_rate", "composite_pctl", "rk", "pool"]]


R = ranked()
R.to_csv("rank_data.csv", index=False)
YMAX = max(105, R.rk.max() * 1.1)


# ---------------------------------------------------------------- matplotlib
def mpl():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK_SOFT, "text.color": INK,
        "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6})
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for name, col in HIGHLIGHT.values():
        p = R[R.name == name].set_index("season").reindex(SEASONS)
        ax.plot(SEASONS, p.rk, color=col, lw=2, marker="o", ms=6.5,
                markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=3)
        last = p.rk.dropna()
        if len(last):
            ax.annotate(name, (last.index[-1], last.iloc[-1]), xytext=(9, 0),
                        textcoords="offset points", color=col, fontsize=9,
                        fontweight="bold", va="center")
    ax.set_yscale("log"); ax.set_yticks(TICKS)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(0.75, YMAX); ax.invert_yaxis()
    ax.set_xticks(SEASONS); ax.set_xlim(2021.75, 2026.95)
    ax.set_ylabel("rank by median % of match runs\n(of ~90 qualified batters)")
    ax.xaxis.grid(False)
    ax.set_title(f"{TITLE}\n{SUB}", fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/ranks_matplotlib.png", dpi=170)
    fig.savefig(f"{OUT}/ranks_matplotlib.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- seaborn
def sea():
    import seaborn as sns
    sns.set_theme(style="whitegrid", rc={
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "grid.color": GRID, "font.family": "DejaVu Sans"})
    pal = {n: c for n, c in HIGHLIGHT.values()}
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    sns.lineplot(data=R, x="season", y="rk", hue="name", palette=pal, marker="o",
                 markersize=8, linewidth=2, ax=ax, markeredgecolor=SURFACE,
                 markeredgewidth=1.3, zorder=3)
    ax.set_yscale("log"); ax.set_yticks(TICKS)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(0.75, YMAX); ax.invert_yaxis()
    ax.set_xticks(SEASONS)
    ax.set_xlabel(""); ax.set_ylabel("rank by median % of match runs")
    ax.legend(title="", frameon=False, ncol=4, loc="lower center",
              bbox_to_anchor=(.5, -.22), fontsize=9)
    ax.set_title(f"seaborn · {TITLE}\n{SUB}", fontsize=11, color=INK, loc="left", pad=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/ranks_seaborn.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- plotnine
def pn9():
    """plotnine has no working log+reverse transform (it warns and drops one), so
    the rank is plotted as -log10(rank) with hand-set breaks: same geometry,
    no transform conflict."""
    import numpy as np
    from plotnine import (ggplot, aes, geom_line, geom_point, labs,
                          scale_y_continuous, scale_x_continuous, scale_colour_manual,
                          theme_minimal, theme, element_text, element_rect)
    d = R.copy()
    d["y"] = -np.log10(d.rk)
    pal = {n: c for n, c in HIGHLIGHT.values()}
    p = (ggplot(d, aes("season", "y", colour="name"))
         + geom_line(size=1.1) + geom_point(size=2.6)
         + scale_colour_manual(values=pal, name="")
         + scale_y_continuous(breaks=[-np.log10(t) for t in TICKS],
                              labels=[str(t) for t in TICKS],
                              limits=(-np.log10(YMAX), -np.log10(0.75)))
         + scale_x_continuous(breaks=SEASONS, limits=(2021.75, 2026.95))
         + labs(x="", y="rank by median % of match runs",
                title=f"plotnine · {TITLE}", subtitle=SUB)
         + theme_minimal()
         + theme(figure_size=(8.4, 4.8), panel_background=element_rect(fill=SURFACE),
                 plot_background=element_rect(fill=SURFACE, colour=SURFACE),
                 plot_title=element_text(ha="left", size=12), legend_position="bottom"))
    p.save(f"{OUT}/ranks_plotnine.png", dpi=170, verbose=False)


# ---------------------------------------------------------------- plotly
def ply():
    import plotly.graph_objects as go
    PLOTLY_CDN = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/3.0.1/plotly.min.js"
    fig = go.Figure()
    for name, col in HIGHLIGHT.values():
        p = R[R.name == name]
        fig.add_trace(go.Scatter(
            x=p.season, y=p.rk, name=name, mode="lines+markers",
            line=dict(color=col, width=2.4),
            marker=dict(size=10, color=col, line=dict(width=1.4, color=SURFACE)),
            customdata=p[["teams", "innings", "runs", "average", "high_score_disp",
                          "median_pct_match_runs", "top_scorer_rate", "composite_pctl",
                          "pool"]].values,
            hovertemplate=(f"<b>{name}</b> · %{{x}}<br>%{{customdata[0]}}<br><br>"
                           "rank <b>%{y:.0f}</b> of %{customdata[8]}<br>"
                           "median %% of match runs %{customdata[5]:.2f}%%<br>"
                           "%{customdata[1]} inns · %{customdata[2]} runs · "
                           "avg %{customdata[3]:.1f} · HS %{customdata[4]}<br>"
                           "composite %{customdata[7]:.1f} · top scorer "
                           "%{customdata[6]:.0f}%% of inns<extra></extra>")))
    fig.update_layout(
        template="simple_white", height=560, margin=dict(l=80, r=40, t=96, b=60),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        title=dict(text=f"{TITLE}<br><span style='font-size:12px;color:{INK_SOFT}'>{SUB}</span>",
                   x=0, xanchor="left", font=dict(size=16, color=INK)),
        xaxis=dict(tickvals=SEASONS, range=[2021.75, 2026.95], gridcolor=GRID, title=""),
        yaxis=dict(type="log", autorange="reversed", tickvals=TICKS,
                   ticktext=[str(t) for t in TICKS], gridcolor=GRID,
                   title="rank by median % of match runs"),
        legend=dict(orientation="h", y=-0.12, x=0, font=dict(size=11)))
    fig.write_html(f"{OUT}/ranks_plotly.html", include_plotlyjs=PLOTLY_CDN,
                   full_html=True, config={"displaylogo": False})


# ---------------------------------------------------------------- altair
def alt_():
    import altair as alt
    base = alt.Chart(R).encode(
        x=alt.X("season:O", title="", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("rk:Q", title="rank by median % of match runs",
                scale=alt.Scale(type="log", reverse=True, domain=[0.75, YMAX]),
                axis=alt.Axis(values=TICKS)),
        color=alt.Color("name:N", title="",
                        scale=alt.Scale(domain=[n for n, _ in HIGHLIGHT.values()],
                                        range=[c for _, c in HIGHLIGHT.values()])))
    line = base.mark_line(strokeWidth=2.4)
    pts = base.mark_point(filled=True, size=110, stroke=SURFACE, strokeWidth=1.4).encode(
        tooltip=[alt.Tooltip("name:N", title="player"),
                 alt.Tooltip("season:O", title="season"),
                 alt.Tooltip("teams:N", title="county"),
                 alt.Tooltip("rk:Q", title="rank", format=".0f"),
                 alt.Tooltip("pool:Q", title="of"),
                 alt.Tooltip("composite_pctl:Q", title="composite", format=".1f"),
                 alt.Tooltip("innings:Q", title="innings"),
                 alt.Tooltip("runs:Q", title="runs"),
                 alt.Tooltip("average:Q", title="average", format=".1f"),
                 alt.Tooltip("median_pct_match_runs:Q", title="median % match runs",
                             format=".2f"),
                 alt.Tooltip("top_scorer_rate:Q", title="top scorer %", format=".0f")])
    chart = (alt.layer(line, pts).properties(
        width=760, height=440,
        title=alt.TitleParams(TITLE, subtitle=SUB, anchor="start", fontSize=15,
                              color=INK, subtitleColor=INK_SOFT))
        .configure_view(fill=SURFACE, stroke=None)
        .configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID,
                        labelColor=INK_SOFT, titleColor=INK_SOFT))
    chart.save(f"{OUT}/ranks_altair.html")


# ---------------------------------------------------------------- bokeh
def bok():
    from bokeh.plotting import figure, save, output_file
    from bokeh.models import ColumnDataSource, HoverTool
    from bokeh.resources import INLINE
    output_file(f"{OUT}/ranks_bokeh.html", title=TITLE)
    p = figure(width=860, height=500, background_fill_color=SURFACE,
               border_fill_color=SURFACE, y_axis_type="log",
               y_range=(YMAX, 0.75), x_range=(2021.75, 2026.95),
               tools="pan,wheel_zoom,box_zoom,reset,save", title=TITLE)
    p.title.text_font_size = "14px"; p.title.text_color = INK
    p.yaxis.axis_label = "rank by median % of match runs"
    p.grid.grid_line_color = GRID; p.xgrid.grid_line_color = None
    p.outline_line_color = None; p.axis.axis_line_color = GRID
    p.axis.major_tick_line_color = GRID
    p.axis.axis_label_text_color = INK_SOFT; p.axis.major_label_text_color = INK_SOFT
    p.xaxis.ticker = SEASONS
    p.yaxis.ticker = TICKS
    for name, col in HIGHLIGHT.values():
        src = ColumnDataSource(R[R.name == name].assign(player_name=name))
        p.line("season", "rk", source=src, color=col, line_width=2.4, legend_label=name)
        p.scatter("season", "rk", source=src, size=10, fill_color=col,
                  line_color=SURFACE, line_width=1.4, legend_label=name)
    p.legend.orientation = "horizontal"; p.legend.location = "top_left"
    p.legend.label_text_font_size = "11px"; p.legend.click_policy = "hide"
    p.legend.background_fill_color = SURFACE; p.legend.border_line_color = None
    p.add_layout(p.legend[0], "below")
    p.add_tools(HoverTool(tooltips="""
        <div style="font:12px system-ui;padding:3px 5px">
          <div style="font-weight:700">@player_name · @season</div>
          <div style="color:#52514e">@teams</div>
          <div style="margin-top:4px">rank <b>@rk{0}</b> of @pool ·
            composite @composite_pctl{0.0}</div>
          <div>@innings inns · @runs runs · avg @average{0.0} · HS @high_score_disp</div>
          <div>median % match runs @median_pct_match_runs{0.00}% ·
            top scorer @top_scorer_rate{0}%</div>
        </div>""", mode="mouse"))
    save(p, resources=INLINE)


if __name__ == "__main__":
    print(R.groupby("name").season.apply(list).to_string())
    mpl(); print("matplotlib ok")
    sea(); print("seaborn ok")
    pn9(); print("plotnine ok")
    ply(); print("plotly ok")
    alt_(); print("altair ok")
    bok(); print("bokeh ok")
