"""Static renderings: matplotlib, seaborn, plotnine.

Batting average against median % of match runs, Division 1 specialist batters.
Six panels each (five seasons plus combined) in three colourings — the four
repeat top-five performers, batting position, county — so 18 panels per library.

In the position and team colourings the four performers keep a dark ring so they
stay findable without hijacking the colour channel.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from chart_common import (load, cuts, limits, legend_for, HIGHLIGHT, SEASONS, MODES,
                          SURFACE, INK, INK_SOFT, GRID, FIELD, ROLE_MARKER,
                          POSITION_COLOUR, TEAM_COLOUR)

OUT = "site/charts"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_SOFT, "text.color": INK,
    "xtick.color": INK_SOFT, "ytick.color": INK_SOFT,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6, "grid.alpha": .7,
})

D = load()
XC, YC = cuts(D)
XL, YL = limits(D)
QUAD = [("r", "t", "Good by both"), ("r", "b", "Flattered by average"),
        ("l", "t", "Undervalued by average"), ("l", "b", "Poor by both")]


def quad_labels(ax):
    pad = .02
    for xq, yq, text in QUAD:
        x = XL[1] - pad * (XL[1] - XL[0]) if xq == "r" else XL[0] + pad * (XL[1] - XL[0])
        y = YL[1] - pad * (YL[1] - YL[0]) if yq == "t" else YL[0] + pad * (YL[1] - YL[0])
        ax.annotate(text, (x, y), ha="right" if xq == "r" else "left",
                    va="top" if yq == "t" else "bottom", fontsize=7.4,
                    color=INK_SOFT, style="italic", zorder=3)


# stack labels vertically on the same side: side-swapping made close pairs collide
OFFSETS = [(8, -2), (8, 13), (8, -17), (8, 28), (8, -32), (8, 43)]


def label_offsets(pts):
    """pts: list of (x, y). Returns an offset per point, alternating within any
    cluster of points close enough that fixed offsets would collide."""
    xr, yr = XL[1] - XL[0], YL[1] - YL[0]
    placed, out = [], []
    for x, y in pts:
        near = sum(1 for px, py in placed
                   if abs(px - x) < .13 * xr and abs(py - y) < .09 * yr)
        out.append(OFFSETS[near % len(OFFSETS)])
        placed.append((x, y))
    return out


def panel(ax, d, title, mode, quads=False, labels=None):
    """labels: default is on for 'performers', off elsewhere."""
    if labels is None:
        labels = mode == "performers"
    ax.axvline(XC, color=GRID, lw=1, zorder=1)
    ax.axhline(YC, color=GRID, lw=1, zorder=1)
    col = f"colour_{mode}"
    is_hl = d.player.isin(HIGHLIGHT)
    for role, mk in ROLE_MARKER.items():
        r = d[(d.role == role) & ~is_hl]
        if len(r):
            ax.scatter(r.average, r.med_pct_match, s=20 if mode != "performers" else 16,
                       marker=mk, color=r[col], edgecolor="none", zorder=2)
    hl = d[is_hl].sort_values("average")
    offs = label_offsets(list(zip(hl.average, hl.med_pct_match)))
    for (_, r), off in zip(hl.iterrows(), offs):
        ax.scatter(r.average, r.med_pct_match, s=60, marker=ROLE_MARKER.get(r.role, "o"),
                   color=r[col], edgecolor=INK if mode != "performers" else SURFACE,
                   linewidth=1.1 if mode != "performers" else 1.3, zorder=4)
        if labels:
            ax.annotate(r.label, (r.average, r.med_pct_match), xytext=off,
                        ha="right" if off[0] < 0 else "left",
                        textcoords="offset points", fontsize=7.4, color=r[col],
                        fontweight="bold", zorder=5)
    if quads:
        quad_labels(ax)
    ax.set_xlim(*XL); ax.set_ylim(*YL)
    ax.set_title(title, fontsize=9.5, color=INK, loc="left", pad=6)


def legend_handles(mode, d):
    if mode == "performers":
        h = [plt.Line2D([], [], marker=m, ls="", color=FIELD, markersize=6, label=r)
             for r, m in ROLE_MARKER.items()]
        return h + [plt.Line2D([], [], marker="o", ls="", color=c, markersize=7, label=n)
                    for n, c in HIGHLIGHT.values()]
    if mode == "position":
        return [plt.Line2D([], [], marker=ROLE_MARKER[r], ls="", color=c, markersize=7,
                           label=r) for r, c in POSITION_COLOUR.items()]
    return [plt.Line2D([], [], marker="o", ls="", color=TEAM_COLOUR[t], markersize=7,
                       label=t) for t in sorted(set(d.teams))]


SUBTITLE = {
    "performers": "coloured by the three best mean season ranks on median share (min 4 qualifying seasons)",
    "position": "coloured by batting position (marker shape matches)",
    "team": "coloured by county — exploratory only; 17 hues are not reliably separable",
}


# ---------------------------------------------------------------- matplotlib
def matplotlib_grid(mode):
    fig, axes = plt.subplots(2, 3, figsize=(13.2, 7.9), sharex=True, sharey=True)
    for ax, yr in zip(axes.flat, SEASONS):
        sub = D[D.season == yr]
        panel(ax, sub, f"{yr}  ·  {len(sub)} batters", mode)
    panel(axes.flat[5], D, f"2022–2026 combined  ·  {len(D)} batter-seasons", mode,
          quads=True, labels=False)
    for ax in axes[1]:
        ax.set_xlabel("batting average")
    for ax in axes[:, 0]:
        ax.set_ylabel("median % of match runs")
    ncol = 9 if mode == "team" else 7
    fig.legend(handles=legend_handles(mode, D), loc="lower center", ncol=ncol,
               frameon=False, fontsize=8.2, bbox_to_anchor=(.5, -.005))
    fig.suptitle("Division 1 batting: the conventional measure against the pitch-normalised one"
                 f"\n{SUBTITLE[mode]}", fontsize=12, color=INK, x=.008, ha="left", y=.995)
    fig.tight_layout(rect=[0, .075 if mode == "team" else .05, 1, .945])
    fig.savefig(f"{OUT}/matplotlib_grid_{mode}.png", dpi=170)
    fig.savefig(f"{OUT}/matplotlib_grid_{mode}.pdf")
    plt.close(fig)


def matplotlib_singles(mode):
    for yr in SEASONS + ["combined"]:
        d = D if yr == "combined" else D[D.season == yr]
        fig, ax = plt.subplots(figsize=(7.6, 5.6))
        label = "2022–2026" if yr == "combined" else yr
        panel(ax, d, f"Division 1 {label}: average vs median % of match runs", mode, quads=True)
        ax.set_xlabel("batting average"); ax.set_ylabel("median % of match runs")
        if mode != "performers":
            ax.legend(handles=legend_handles(mode, d), frameon=False, fontsize=7.4,
                      loc="lower right", ncol=2 if mode == "team" else 1)
        fig.tight_layout()
        fig.savefig(f"{OUT}/matplotlib_{mode}_{yr}.png", dpi=170)
        plt.close(fig)


# ---------------------------------------------------------------- seaborn
def seaborn_facets(mode):
    both = pd.concat([D.assign(panel=D.season.astype(str)),
                      D.assign(panel="2022–2026")], ignore_index=True)
    sns.set_theme(style="whitegrid", rc={
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "grid.color": GRID, "font.family": "DejaVu Sans"})
    pal = legend_for(mode, D)
    gcol = f"group_{mode}"
    if mode == "performers":
        pal = {**pal, "Other batters": FIELD}
    g = sns.relplot(data=both, x="average", y="med_pct_match", col="panel", col_wrap=3,
                    kind="scatter", hue=gcol, palette=pal, style="role",
                    markers=list(ROLE_MARKER.values()), s=40, height=2.9, aspect=1.25,
                    facet_kws={"sharex": True, "sharey": True},
                    hue_order=list(pal), legend="brief")
    for panel_name, ax in g.axes_dict.items():
        ax.axvline(XC, color=GRID, lw=1); ax.axhline(YC, color=GRID, lw=1)
        ax.set_title(panel_name, fontsize=10, loc="left")
    g.set_axis_labels("batting average", "median % of match runs")
    sns.move_legend(g, "lower center", ncol=6 if mode == "team" else 4, frameon=False,
                    bbox_to_anchor=(.5, -.02), fontsize=8, title=None)
    g.figure.suptitle(f"seaborn · relplot facets — {SUBTITLE[mode]}", x=.008, ha="left",
                      y=1.0, fontsize=11)
    g.figure.subplots_adjust(top=.90, bottom=.17 if mode == "team" else .12)
    g.savefig(f"{OUT}/seaborn_facets_{mode}.png", dpi=170)
    plt.close(g.figure)


# ---------------------------------------------------------------- plotnine
def plotnine_facets(mode):
    from plotnine import (ggplot, aes, geom_point, geom_vline, geom_hline, facet_wrap,
                          labs, theme_minimal, theme, element_text, element_rect,
                          scale_colour_manual, scale_shape_manual, guides, guide_legend)
    both = pd.concat([D.assign(panel=D.season.astype(str)),
                      D.assign(panel="2022–2026")], ignore_index=True)
    pal = dict(legend_for(mode, D))
    if mode == "performers":
        pal["Other batters"] = FIELD
    p = (ggplot(both, aes("average", "med_pct_match"))
         + geom_vline(xintercept=XC, colour=GRID)
         + geom_hline(yintercept=YC, colour=GRID)
         + geom_point(aes(colour=f"group_{mode}", shape="role"), size=2, alpha=.95)
         + scale_colour_manual(values=pal, name="")
         + scale_shape_manual(values=["^", "s", "o"], name="position")
         + facet_wrap("panel", ncol=3)
         + labs(x="batting average", y="median % of match runs",
                title=f"plotnine · grammar of graphics — {SUBTITLE[mode]}")
         + guides(colour=guide_legend(ncol=6 if mode == "team" else 4))
         + theme_minimal()
         + theme(figure_size=(13, 7.8), panel_background=element_rect(fill=SURFACE),
                 plot_background=element_rect(fill=SURFACE, colour=SURFACE),
                 plot_title=element_text(ha="left", size=12), legend_position="bottom"))
    p.save(f"{OUT}/plotnine_facets_{mode}.png", dpi=170, verbose=False)


if __name__ == "__main__":
    for mode in MODES:
        matplotlib_grid(mode); matplotlib_singles(mode)
        seaborn_facets(mode)
        plotnine_facets(mode)
        print(f"{mode}: matplotlib + seaborn + plotnine ok")
