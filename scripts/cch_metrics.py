"""
Pitch-normalised, share-of-runs player rankings for the County Championship.

Metrics (per player, within a chosen division / season range):

  pct_runs_at_home_ground   player's runs made at his own team's home ground,
                            as % of all his runs in scope
  share_team_runs           player's runs / his team's totals in the innings he batted
  share_team_runs_home      same, restricted to matches at his team's home ground
  share_team_runs_away      same, restricted to away matches
  home_away_gap             home minus away share (positive = home-ground flattered)
  mean_pct_match_runs       per match: player's runs / all runs scored in the match
                            (all four innings, both teams, extras included); mean
  median_pct_match_runs     ... median
  n_top_scorer              innings finishing as top run scorer
  n_top3                    innings finishing in the top 3 run scorers
  top_scorer_rate           n_top_scorer / innings
  top3_rate                 n_top3 / innings
  high_score                best individual innings in scope (high_score_disp adds * if not out)
  bdry_pct                  % of his runs made in fours and sixes
  bdry_freq                 boundaries per 100 balls faced
  rotate                    runs per 100 balls that did not go to the boundary
  role                      band holding most of his innings: 1-2 Opener, 3-5 Middle order,
                            6-7 All-rounder / keeper, 8-11 Lower order (role_share = that %)

Run:  python3 cch_metrics.py           (division 1)
      python3 cch_metrics.py --division 2 --min-innings 30
"""
import argparse
import numpy as np
import pandas as pd


def load(division=None, seasons=None):
    b = pd.read_csv("innings_bat.csv")
    m = pd.read_csv("matches.csv")
    if division is not None:
        b = b[b.division == division]
        m = m[m.division == division]
    if seasons:
        b = b[b.season.isin(seasons)]
        m = m[m.season.isin(seasons)]
    return b, m


def player_metrics(b, group_cols=("player_id",), min_innings=1):
    """b: innings-level batting rows, already filtered to the scope of interest."""
    g = list(group_cols)

    # ---- match level: a player's runs in a match vs all runs scored in that match
    match = (b.groupby(g + ["match_id", "match_runs", "match_bat_runs", "at_home_ground"],
                       as_index=False)["runs"].sum())
    match["pct_match_runs"] = 100 * match.runs / match.match_runs
    match["pct_match_bat_runs"] = 100 * match.runs / match.match_bat_runs

    mm = match.groupby(g).agg(
        matches=("match_id", "nunique"),
        runs_total=("runs", "sum"),
        mean_pct_match_runs=("pct_match_runs", "mean"),
        median_pct_match_runs=("pct_match_runs", "median"),
        sd_pct_match_runs=("pct_match_runs", "std"),
        max_pct_match_runs=("pct_match_runs", "max"),
        mean_pct_match_bat_runs=("pct_match_bat_runs", "mean"),
        median_pct_match_bat_runs=("pct_match_bat_runs", "median"),
    )

    # ---- innings level: rank within innings, team-share, home/away splits
    b = b.copy()
    b["is_top"] = b.inn_rank == 1
    b["is_top3"] = b.inn_rank <= 3
    ii = b.groupby(g).agg(
        player=("player", lambda s: s.mode().iat[0]),
        teams=("team", lambda s: "/".join(sorted(s.unique()))),
        seasons=("season", lambda s: f"{s.min()}-{s.max()}" if s.min() != s.max() else str(s.min())),
        innings=("runs", "size"),
        runs=("runs", "sum"),
        balls=("balls", "sum"),
        fours=("fours", "sum"),
        sixes=("sixes", "sum"),
        dismissals=("out", "sum"),
        hundreds=("runs", lambda s: int((s >= 100).sum())),
        fifties=("runs", lambda s: int(((s >= 50) & (s < 100)).sum())),
        n_top_scorer=("is_top", "sum"),
        n_top3=("is_top3", "sum"),
        high_score=("runs", "max"),
        team_runs_in_those_innings=("team_total", "sum"),
    )
    # was the highest score a not-out? (first innings reaching it, if tied)
    hs_idx = b.groupby(g)["runs"].idxmax()
    hs_no = b.loc[hs_idx].set_index(g)["out"].map(lambda o: not bool(o))
    ii["high_score_not_out"] = hs_no
    ii["high_score_disp"] = (ii.high_score.astype(int).astype(str)
                             + np.where(ii.high_score_not_out, "*", ""))

    ii["average"] = ii.runs / ii.dismissals.replace(0, np.nan)
    ii["strike_rate"] = 100 * ii.runs / ii.balls.replace(0, np.nan)
    # Cricsheet carries no all-run-four flag in this archive, so a boundary is any
    # 4 or 6 off the bat; a handful of all-run fours are counted as boundaries.
    ii["bdry_runs"] = 4 * ii.fours + 6 * ii.sixes
    ii["bdry_pct"] = 100 * ii.bdry_runs / ii.runs.replace(0, np.nan)
    ii["bdry_freq"] = 100 * (ii.fours + ii.sixes) / ii.balls.replace(0, np.nan)
    # runs per 100 balls that did not go to the boundary: a strike-rotation proxy.
    # Root and Hain share a boundary %, but Root's comes from rotating at ~40 and
    # Hain's from hitting far fewer boundaries while rotating at the pool median.
    ii["rotate"] = (100 * (ii.runs - ii.bdry_runs)
                    / (ii.balls - ii.fours - ii.sixes).replace(0, np.nan))
    ii["share_team_runs"] = 100 * ii.runs / ii.team_runs_in_those_innings
    ii["top_scorer_rate"] = 100 * ii.n_top_scorer / ii.innings
    ii["top3_rate"] = 100 * ii.n_top3 / ii.innings

    # ---- batting position mix and role
    # role = the band holding the largest share of a player's innings
    bands = {"pct_pos_1_2": (1, 2), "pct_pos_3_5": (3, 5),
             "pct_pos_6_7": (6, 7), "pct_pos_8_11": (8, 99)}
    for col, (lo, hi) in bands.items():
        ii[col] = 100 * (b[(b.bat_pos >= lo) & (b.bat_pos <= hi)]
                         .groupby(g)["runs"].size().reindex(ii.index).fillna(0)) / ii.innings
    ROLE = {"pct_pos_1_2": "Opener", "pct_pos_3_5": "Middle order",
            "pct_pos_6_7": "All-rounder / keeper", "pct_pos_8_11": "Lower order"}
    bandcols = list(bands)
    ii["role"] = ii[bandcols].idxmax(axis=1).map(ROLE)
    ii["role_share"] = ii[bandcols].max(axis=1)
    ii["median_bat_pos"] = b.groupby(g)["bat_pos"].median()

    # ---- home / away splits
    def split(mask, suffix):
        sub = b[mask]
        s = sub.groupby(g).agg(**{
            f"innings_{suffix}": ("runs", "size"),
            f"runs_{suffix}": ("runs", "sum"),
            f"team_runs_{suffix}": ("team_total", "sum"),
            f"n_top_scorer_{suffix}": ("is_top", "sum"),
        })
        s[f"share_team_runs_{suffix}"] = 100 * s[f"runs_{suffix}"] / s[f"team_runs_{suffix}"]
        return s

    home = split(b.at_home_ground == True, "home")
    away = split(b.at_home_ground == False, "away")

    out = ii.join(mm).join(home).join(away)
    out["pct_runs_at_home_ground"] = 100 * out.runs_home.fillna(0) / out.runs
    out["home_away_gap"] = out.share_team_runs_home - out.share_team_runs_away

    # home share of the player's *match-level* share of all match runs
    hm = match[match.at_home_ground == True].groupby(g)["pct_match_runs"].median()
    am = match[match.at_home_ground == False].groupby(g)["pct_match_runs"].median()
    out["median_pct_match_runs_home"] = hm
    out["median_pct_match_runs_away"] = am

    out = out[out.innings >= min_innings]
    # percentile ranks within the qualifying pool, for easy composite ranking
    for c in ["share_team_runs", "median_pct_match_runs", "top_scorer_rate", "top3_rate"]:
        out["pctl_" + c] = (100 * out[c].rank(pct=True)).round(1)
    out["composite_pctl"] = out[["pctl_share_team_runs", "pctl_median_pct_match_runs",
                                 "pctl_top_scorer_rate", "pctl_top3_rate"]].mean(axis=1).round(1)
    cols = ["player", "teams", "seasons", "innings", "matches", "runs", "balls",
            "average", "high_score", "high_score_not_out", "high_score_disp",
            "hundreds", "fifties", "strike_rate",
            "fours", "sixes", "bdry_runs", "bdry_pct", "bdry_freq", "rotate",
            "role", "role_share", "median_bat_pos",
            "pct_pos_1_2", "pct_pos_3_5", "pct_pos_6_7", "pct_pos_8_11",
            "share_team_runs", "share_team_runs_home", "share_team_runs_away",
            "home_away_gap", "pct_runs_at_home_ground",
            "mean_pct_match_runs", "median_pct_match_runs", "sd_pct_match_runs",
            "max_pct_match_runs", "mean_pct_match_bat_runs", "median_pct_match_bat_runs",
            "median_pct_match_runs_home", "median_pct_match_runs_away",
            "n_top_scorer", "n_top3", "top_scorer_rate", "top3_rate",
            "innings_home", "innings_away", "runs_home", "runs_away",
            "pctl_share_team_runs", "pctl_median_pct_match_runs",
            "pctl_top_scorer_rate", "pctl_top3_rate", "composite_pctl"]
    out = out[[c for c in cols if c in out.columns]]
    return out.round(3).sort_values("median_pct_match_runs", ascending=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--division", type=int, default=1)
    ap.add_argument("--min-innings", type=int, default=40)
    ap.add_argument("--min-innings-season", type=int, default=8)
    ap.add_argument("--seasons", type=int, nargs="*")
    ap.add_argument("--exclude-2021", action="store_true",
                    help="drop 2021, when the competition ran as three conference groups "
                         "rather than two divisions")
    a = ap.parse_args()

    b, m = load(a.division, a.seasons)
    if a.exclude_2021:
        b, m = b[b.season != 2021], m[m.season != 2021]
    print(f"division {a.division}: {m.shape[0]} matches, {b.shape[0]} batting innings, "
          f"seasons {b.season.min()}-{b.season.max()}")

    career = player_metrics(b, ("player_id",), a.min_innings)
    career.to_csv(f"player_rankings_div{a.division}_career.csv")
    season = player_metrics(b, ("player_id", "season"), a.min_innings_season)
    season.to_csv(f"player_rankings_div{a.division}_by_season.csv")
    print(f"career rows {len(career)} (min {a.min_innings} inns), "
          f"season rows {len(season)} (min {a.min_innings_season} inns)")
