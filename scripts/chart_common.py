"""Shared data prep and design tokens for the average-vs-share scatter plots.

x = batting average          (the conventional measure)
y = median % of match runs   (the pitch-normalised one)

Scope: Division 1, 2022-2026, minimum 12 innings in a season, specialist batters
only (roles 1-7). Nos 8-11 are excluded rather than clipped by an axis floor:
they crowd the bottom-left corner and are not really in this comparison, while
clipping would also hide the poor top-order batters we do want to see.
"""
import pandas as pd

SEASONS = [2022, 2023, 2024, 2025, 2026]
MIN_INNINGS = 12

# validated all-pairs under the dataviz checker (light surface):
# worst CVD dE 9.2, worst normal-vision dE 16.3
# Chosen on median % of match runs alone. Of the 34 players with at least four
# qualifying Division 1 seasons in 2022-26, these three have the best mean season
# rank (11.6, 16.4, 20.0); below them sit five players inside 0.85 of a rank of
# each other, so the cut falls in a real gap rather than an arbitrary top-N.
# Three slots also clear the all-pairs colour check a scatter needs.
HIGHLIGHT = {
    "SR Hain":  ("Sam Hain",   "#2a78d6"),
    "TB Abell": ("Tom Abell",  "#eb6834"),
    "JM Cox":   ("Jordan Cox", "#1baf7a"),
}
SURFACE = "#fcfcfb"
INK, INK_SOFT, GRID, FIELD = "#0b0b0b", "#52514e", "#e3e2de", "#c2c1bb"

ROLE_MARKER = {"Opener": "o", "Middle order": "s", "All-rounder / keeper": "^"}

# --- colour modes ------------------------------------------------------------
# "performers"  the three best mean season ranks on median share, else grey
# "position"    the three specialist bands; first three palette slots, which are
#               the set that validates under the all-pairs rule a scatter needs
# "team"        17 counties appear across 2022-26 (10 in any one season). No
#               17-colour scheme stays separable, for colourblind readers least
#               of all, so this mode is exploratory: identity comes from the
#               hover and the click-to-isolate legend in the interactive
#               versions, and colour only groups points by eye.
POSITION_COLOUR = {"Opener": "#2a78d6", "Middle order": "#eb6834",
                   "All-rounder / keeper": "#1baf7a"}

COUNTIES = ["Derbyshire", "Durham", "Essex", "Glamorgan", "Gloucestershire",
            "Hampshire", "Kent", "Lancashire", "Leicestershire", "Middlesex",
            "Northamptonshire", "Nottinghamshire", "Somerset", "Surrey", "Sussex",
            "Warwickshire", "Worcestershire", "Yorkshire"]


def _team_palette(names=COUNTIES):
    """Deterministic, evenly spaced hues at two lightness levels. Spacing hues
    this way keeps neighbours apart by eye; it is NOT colourblind-safe at this
    count, which is why this mode leans on hover and legend isolation."""
    import colorsys
    out, n = {}, len(names)
    half = (n + 1) // 2
    for i, name in enumerate(names):
        band = i % 2                       # alternate dark / mid so the list interleaves
        hue = ((i // 2) / half + (0.5 / half if band else 0)) % 1.0
        light, sat = (0.36, 0.72) if band == 0 else (0.56, 0.62)
        r, g, b = colorsys.hls_to_rgb(hue, light, sat)
        out[name] = "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))
    return out


TEAM_COLOUR = _team_palette()

MODES = {
    "performers": "the three best mean season ranks on median share",
    "position":   "batting position band",
    "team":       "county",
}


def colour_of(row, mode):
    if mode == "position":
        return POSITION_COLOUR.get(row.role, FIELD)
    if mode == "team":
        return TEAM_COLOUR.get(row.teams, FIELD)
    return HIGHLIGHT[row.player][1] if row.player in HIGHLIGHT else FIELD


def legend_for(mode, d):
    """Ordered {label: colour} for the mode, limited to what is present."""
    if mode == "position":
        return {k: v for k, v in POSITION_COLOUR.items() if k in set(d.role)}
    if mode == "team":
        return {t: TEAM_COLOUR[t] for t in sorted(set(d.teams)) if t in TEAM_COLOUR}
    return {n: c for n, c in HIGHLIGHT.values()}


def group_of(row, mode):
    if mode == "position":
        return row.role
    if mode == "team":
        return row.teams
    return HIGHLIGHT[row.player][0] if row.player in HIGHLIGHT else "Other batters"

QUADRANTS = [
    ("high", "high", "Good by both measures"),
    ("high", "low",  "Flattered by average\n— runs came in run-gluts"),
    ("low",  "high", "Undervalued by average\n— runs when they were hard"),
    ("low",  "low",  "Poor by both measures"),
]


def load(division=1, seasons=SEASONS, min_innings=MIN_INNINGS, specialists_only=True):
    s = pd.read_csv(f"player_rankings_div{division}_by_season.csv")
    d = s[(s.season.isin(seasons)) & (s.innings >= min_innings)].copy()
    if specialists_only:
        d = d[d.role != "Lower order"]
    d["highlight"] = d.player.map(lambda p: HIGHLIGHT[p][0] if p in HIGHLIGHT else "")
    d["label"] = d.apply(
        lambda r: f"{r.highlight.split()[-1]} {int(r.season) % 100:02d}" if r.highlight else "",
        axis=1)
    for mode in ("performers", "position", "team"):
        d[f"colour_{mode}"] = d.apply(lambda r: colour_of(r, mode), axis=1)
        d[f"group_{mode}"] = d.apply(lambda r: group_of(r, mode), axis=1)
    d["colour"] = d["colour_performers"]
    d = d.rename(columns={"median_pct_match_runs": "med_pct_match",
                          "share_team_runs": "pct_team_runs"})
    cols = ["season", "player", "teams", "role", "median_bat_pos", "innings", "runs",
            "average", "strike_rate", "bdry_pct", "bdry_freq", "rotate",
            "high_score_disp", "med_pct_match", "pct_team_runs",
            "top_scorer_rate", "top3_rate", "n_top_scorer", "n_top3",
            "home_away_gap", "composite_pctl", "highlight", "label", "colour",
            "colour_performers", "colour_position", "colour_team",
            "group_performers", "group_position", "group_team"]
    return d[cols].sort_values(["season", "average"]).reset_index(drop=True)


def cuts(d):
    """Quadrant split points: the field medians of whatever is plotted."""
    return float(d.average.median()), float(d.med_pct_match.median())


def limits(d, pad=0.06):
    """Axis limits with a little padding; keeps every plotted point on screen."""
    xr = d.average.max() - d.average.min()
    yr = d.med_pct_match.max() - d.med_pct_match.min()
    return ((d.average.min() - pad * xr, d.average.max() + pad * xr),
            (max(0, d.med_pct_match.min() - pad * yr), d.med_pct_match.max() + pad * yr))


if __name__ == "__main__":
    d = load()
    d.to_csv("scatter_data.csv", index=False)
    print(d.shape, "rows")
    print("per season:", d.groupby("season").size().to_dict())
    print("cuts (avg, med%):", [round(c, 2) for c in cuts(d)])
    print("highlighted rows:", int((d.highlight != "").sum()))
    print(d[d.highlight != ""][["season", "player", "average", "med_pct_match"]]
          .to_string(index=False))
