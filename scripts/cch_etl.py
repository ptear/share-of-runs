"""
County Championship player-level batting analysis from Cricsheet ball-by-ball JSON.

Builds two fact tables:
  innings_bat.csv  - one row per (match, innings, batter)
  matches.csv      - one row per match

Then computes pitch-normalised, share-of-runs metrics per player.
"""
import json, os, glob, collections
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def load_matches(data_dir=DATA_DIR):
    # match files are named by their Cricsheet id (e.g. 1068528.json); ignore
    # anything else that happens to live in the directory
    files = sorted(f for f in glob.glob(os.path.join(data_dir, "*.json"))
                   if os.path.basename(f)[:-5].isdigit())
    raw = []
    for f in files:
        with open(f) as fh:
            d = json.load(fh)
        d["_id"] = os.path.basename(f).replace(".json", "")
        raw.append(d)
    return raw


def infer_home_venues(raw):
    """Cricsheet has no home/away flag. Assign each venue to the team that
    appears there most often across the whole archive; that team is 'home'."""
    cnt = collections.Counter()
    for d in raw:
        v = d["info"].get("venue")
        for t in d["info"]["teams"]:
            cnt[(v, t)] += 1
    by_venue = collections.defaultdict(dict)
    for (v, t), n in cnt.items():
        by_venue[v][t] = n
    owner, shares = {}, {}
    for v, teams in by_venue.items():
        n_matches = sum(teams.values()) / 2          # two teams per match
        t, n = max(teams.items(), key=lambda kv: kv[1])
        owner[v] = t
        shares[v] = n / n_matches                    # 1.0 == team present at every match here
    return owner, shares


def build_tables(raw):
    owner, shares = infer_home_venues(raw)
    mrows, brows = [], []

    for d in raw:
        info = d["info"]
        mid = d["_id"]
        venue = info.get("venue")
        teams = info["teams"]
        home = owner.get(venue)
        if home not in teams:          # neutral / outground not owned by either side
            home = None
        away = [t for t in teams if t != home][0] if home else None
        div = info.get("event", {}).get("group")
        reg = info.get("registry", {}).get("people", {})

        per_inn = []
        for i, inn in enumerate(d.get("innings", []), start=1):
            bat_team = inn["team"]
            runs = collections.Counter()
            balls = collections.Counter()
            fours = collections.Counter()
            sixes = collections.Counter()
            outs = set()
            order, seen = {}, 0
            team_total = 0
            pen = inn.get("penalty_runs", {})
            team_total += pen.get("pre", 0) + pen.get("post", 0)
            for ov in inn.get("overs", []):
                for ball in ov.get("deliveries", []):
                    b = ball["batter"]
                    # register striker AND non-striker in arrival order, so an opener
                    # who doesn't take strike still gets position 2 rather than 3
                    for who in (b, ball.get("non_striker")):
                        if who and who not in order:
                            seen += 1
                            order[who] = seen
                    r = ball["runs"]
                    runs[b] += r["batter"]
                    team_total += r["total"]
                    ex = ball.get("extras", {})
                    # wides are not balls faced
                    if "wides" not in ex:
                        balls[b] += 1
                    if r["batter"] == 4:
                        fours[b] += 1
                    if r["batter"] == 6:
                        sixes[b] += 1
                    for w in ball.get("wickets", []):
                        if w.get("kind") in ("retired hurt", "retired not out"):
                            continue
                        if w.get("player_out"):
                            outs.add(w["player_out"])
            for who in order:
                if who not in runs:
                    runs[who] = 0          # came to the crease, never faced a ball
            per_inn.append(dict(inn_no=i, bat_team=bat_team, team_total=team_total,
                                runs=runs, balls=balls, fours=fours, sixes=sixes,
                                outs=outs, order=order,
                                declared=bool(inn.get("declared")),
                                forfeited=bool(inn.get("forfeited"))))

        match_runs = sum(x["team_total"] for x in per_inn)
        match_bat_runs = sum(sum(x["runs"].values()) for x in per_inn)

        mrows.append(dict(match_id=mid, season=info.get("season"), division=div,
                          date=info["dates"][0], venue=venue, city=info.get("city"),
                          home_team=home, away_team=away, venue_home_share=shares.get(venue),
                          team_a=teams[0], team_b=teams[1],
                          result=info.get("outcome", {}).get("result")
                          or info.get("outcome", {}).get("winner"),
                          innings_count=len(per_inn),
                          match_runs=match_runs, match_bat_runs=match_bat_runs))

        for x in per_inn:
            bt = x["bat_team"]
            opp = [t for t in teams if t != bt]
            opp = opp[0] if opp else None
            tot = x["team_total"]
            # rank within innings by runs (dense-ish: ties share the best rank)
            srt = sorted(x["runs"].items(), key=lambda kv: -kv[1])
            rank = {}
            prev_runs, prev_rank = None, 0
            for idx, (p, r) in enumerate(srt, start=1):
                if r != prev_runs:
                    prev_rank, prev_runs = idx, r
                rank[p] = prev_rank
            n_bat = len(srt)
            for p, r in x["runs"].items():
                brows.append(dict(
                    match_id=mid, season=info.get("season"), division=div,
                    date=info["dates"][0], venue=venue, inn_no=x["inn_no"],
                    team=bt, opposition=opp, player=p, player_id=reg.get(p),
                    runs=r, balls=x["balls"][p], fours=x["fours"][p], sixes=x["sixes"][p],
                    out=p in x["outs"], bat_pos=x["order"][p],
                    team_total=tot, team_bat_runs=sum(x["runs"].values()),
                    match_runs=match_runs, match_bat_runs=match_bat_runs,
                    inn_rank=rank[p], n_batted=n_bat,
                    is_home=(bt == home) if home else None,
                    at_home_ground=(bt == home) if home else None,
                ))

    return pd.DataFrame(mrows), pd.DataFrame(brows)


if __name__ == "__main__":
    raw = load_matches()
    m, b = build_tables(raw)
    m.to_csv("matches.csv", index=False)
    b.to_csv("innings_bat.csv", index=False)
    print(m.shape, b.shape)
    print(m.head())
    print(b.head())
