"""Assemble the static site: table page, chart gallery, data downloads, README.

Output in site/ is ready to push to a GitHub Pages branch, and the same two
pages are what get published as an artifact.
"""
import json, os, shutil
import pandas as pd

SITE = "site"
os.makedirs(f"{SITE}/data", exist_ok=True)
os.makedirs(f"{SITE}/charts", exist_ok=True)

NAV = """<nav class="nav">
  <a class="brand" href="index.html">Share of Runs</a>
  <a href="index.html" data-page="index">Rankings table</a>
  <a href="charts.html" data-page="charts">Average vs share</a>
  <a href="data/">Data</a>
</nav>"""

NAV_CSS = """
.nav{display:flex; gap:18px; align-items:baseline; flex-wrap:wrap;
  padding-block:0 18px; margin-bottom:22px; border-bottom:1px solid var(--rule)}
.nav a{color:var(--ink-soft); text-decoration:none; font-size:13px}
.nav a:hover{color:var(--turf)}
.nav a[aria-current="page"]{color:var(--turf); font-weight:600}
.nav .brand{font-family:Bitter,Georgia,serif; font-weight:700; font-size:15px;
  color:var(--ink); margin-right:6px}
"""

DOCTYPE = "<!doctype html>\n<html lang=\"en\">\n"
HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
"""


PAYLOAD_COLS = ["player", "teams", "median_bat_pos", "role", "role_share", "innings",
                "runs", "average", "strike_rate", "high_score", "high_score_disp",
                "bdry_pct", "bdry_freq", "rotate",
                "share_team_runs", "share_team_runs_home", "share_team_runs_away",
                "home_away_gap", "pct_runs_at_home_ground", "mean_pct_match_runs",
                "median_pct_match_runs", "n_top_scorer", "top_scorer_rate",
                "n_top3", "top3_rate", "composite_pctl"]


def build_payload(path="leaderboard.json"):
    """Career + per-season tables for both divisions, as one JSON blob for the page."""
    def recs(df, cols):
        df = df[cols].round(2)
        return df.astype(object).where(pd.notna(df), None).to_dict("records")

    out, seasons = {}, set()
    for div in (1, 2):
        c = pd.read_csv(f"player_rankings_div{div}_career.csv")
        out[f"div{div}_career"] = recs(c, PAYLOAD_COLS + ["seasons"])
        s = pd.read_csv(f"player_rankings_div{div}_by_season.csv")
        for yr, grp in s.groupby("season"):
            seasons.add(int(yr))
            out[f"div{div}_{yr}"] = recs(grp, PAYLOAD_COLS)
    out["_seasons"] = sorted(seasons)
    txt = json.dumps(out, separators=(",", ":"), allow_nan=False)  # NaN is not valid JSON
    open(path, "w").write(txt)
    return txt


def build_index():
    frag = open("page_template.html").read()
    data = build_payload()
    frag = frag.replace("__DATA__", data)
    # nav + head, and mark the current page
    frag = frag.replace("</style>", NAV_CSS + "</style>")
    frag = frag.replace('<div class="wrap">',
                        '<div class="wrap">\n  ' + NAV.replace(
                            '<a href="index.html" data-page="index">',
                            '<a href="index.html" data-page="index" aria-current="page">'))
    open(f"{SITE}/index.html", "w").write(DOCTYPE + HEAD + frag + "\n</html>\n")
    # the artifact wrapper supplies its own doctype/head, so it gets a fragment
    open("artifact_page.html", "w").write(HEAD + frag)
    return len(frag)


LIBS = [
    ("plotly", "Plotly", "interactive", "Season buttons across the top; hover any point."),
    ("altair", "Altair", "interactive", "Vega-Lite. Season dropdown below the chart; click a legend entry to isolate it."),
    ("bokeh", "Bokeh", "interactive", "Season dropdown above the chart; click legend entries to hide series. BokehJS is inlined, so this page is ~2 MB."),
    ("matplotlib", "Matplotlib", "static", "All six panels in one image, drawn directly."),
    ("seaborn", "Seaborn", "static", "relplot facets over the same data."),
    ("plotnine", "plotnine", "static", "Grammar of graphics, ggplot2-style."),
]
MODE_LABEL = {"performers": "Top performers", "position": "Batting position", "team": "County"}
MODE_NOTE = {
    "performers": "Coloured: the three players with the best mean season rank on median share "
                  "of match runs, among the 34 with at least four qualifying Division 1 seasons "
                  "since 2022. Their means are 11.6, 16.4 and 20.0; the next five sit between "
                  "22.4 and 23.3, so the cut falls in a real gap rather than at an arbitrary "
                  "top-N. Everyone else is grey; marker shape shows batting position.",
    "position": "Coloured by the band holding most of a player's innings. The three highlighted "
                "batters keep a dark ring so they stay findable.",
    "team": "Coloured by county. Seventeen counties appear across the five seasons and no "
            "seventeen-colour scheme stays reliably separable — least of all for colourblind "
            "readers — so treat this as exploratory: identify points from the hover in the "
            "interactive versions rather than from the colour alone.",
}


RANK_FILE = {"plotly": "charts/ranks_plotly.html", "altair": "charts/ranks_altair.html",
             "bokeh": "charts/ranks_bokeh.html", "matplotlib": "charts/ranks_matplotlib.png",
             "seaborn": "charts/ranks_seaborn.png", "plotnine": "charts/ranks_plotnine.png"}

RANK_NOTE = ("Rank on median % of match runs within each season's qualified pool "
             "(12 innings, 84–98 batters), best at the top on a log scale. A gap is a "
             "season the player did not qualify — Cox has no 2026 — and is left open "
             "rather than interpolated.")


def static_file(lib, mode):
    return (f"charts/matplotlib_grid_{mode}.png" if lib == "matplotlib"
            else f"charts/{lib}_facets_{mode}.png")


def build_charts():
    pressed = ' aria-pressed="true"'
    tabs_lib = "".join(
        f'<button class="tab" data-lib="{k}"{pressed if i == 0 else ""}>{name}</button>'
        for i, (k, name, _, _) in enumerate(LIBS))
    tabs_mode = "".join(
        f'<button class="tab" data-mode="{m}"{pressed if i == 0 else ""}>'
        f'{MODE_LABEL[m]}</button>' for i, m in enumerate(MODE_LABEL))
    panes = []
    for lib, name, kind, blurb in LIBS:
        for mode in MODE_LABEL:
            src = (f"charts/{lib}_{mode}.html" if kind == "interactive"
                   else static_file(lib, mode))
            body = (f'<iframe src="{src}" title="{name}, {MODE_LABEL[mode]}" loading="lazy">'
                    f'</iframe>' if kind == "interactive"
                    else f'<a href="{src}"><img src="{src}" alt="{name}, {MODE_LABEL[mode]}" '
                         f'loading="lazy"></a>')
            panes.append(
                f'<section class="pane" data-lib="{lib}" data-chart="scatter" '
                f'data-mode="{mode}" hidden>'
                f'<p class="blurb"><b>{name}</b> — {blurb}</p>'
                f'{body}'
                f'<p class="open"><a href="{src}" target="_blank" rel="noopener">'
                f'Open this view on its own →</a></p></section>')
    for lib, name, kind, blurb in LIBS:
        src = RANK_FILE[lib]
        body = (f'<iframe src="{src}" title="{name}, rank trajectory" loading="lazy"></iframe>'
                if kind == "interactive"
                else f'<a href="{src}"><img src="{src}" alt="{name}, rank trajectory" '
                     f'loading="lazy"></a>')
        panes.append(
            f'<section class="pane" data-lib="{lib}" data-chart="ranks" hidden>'
            f'<p class="blurb"><b>{name}</b> — {blurb}</p>{body}'
            f'<p class="open"><a href="{src}" target="_blank" rel="noopener">'
            f'Open this view on its own →</a></p></section>')

    html = f"""{DOCTYPE}{HEAD}<title>Average vs Share</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{--ground:#f4f5f0; --panel:#fff; --ink:#1b2620; --ink-soft:#5c6a62; --rule:#dcdfd6;
  --rule-soft:#e9ebe3; --turf:#3f6b4c; --turf-soft:#e2ece4; --shade:#8a9a8f}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{
  --ground:#121613; --panel:#191f1b; --ink:#e7ece7; --ink-soft:#9daba2; --rule:#2b3630;
  --rule-soft:#222b26; --turf:#7fbd92; --turf-soft:#1f2d24; --shade:#6f7f75}}}}
:root[data-theme="dark"]{{--ground:#121613; --panel:#191f1b; --ink:#e7ece7;
  --ink-soft:#9daba2; --rule:#2b3630; --rule-soft:#222b26; --turf:#7fbd92;
  --turf-soft:#1f2d24; --shade:#6f7f75}}
*{{box-sizing:border-box}}
body{{background:var(--ground); color:var(--ink); margin:0; padding-inline:16px;
  padding-block:28px 56px; font-family:"IBM Plex Sans",system-ui,sans-serif}}
.wrap{{max-width:1120px; margin:0 auto}}
h1{{font-family:Bitter,Georgia,serif; font-size:clamp(24px,3.6vw,34px); margin:0 0 6px;
  text-wrap:balance}}
.sub{{color:var(--ink-soft); max-width:66ch; line-height:1.55; font-size:14.5px; margin:0 0 20px}}
{NAV_CSS}
.controls{{display:flex; flex-wrap:wrap; gap:8px 20px; align-items:center; margin-bottom:6px}}
.group{{display:flex; flex-wrap:wrap; gap:6px; align-items:center}}
.group .lab{{font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--shade); margin-right:4px}}
.tab{{appearance:none; border:1px solid var(--rule); background:var(--panel);
  color:var(--ink-soft); font:500 12.5px "IBM Plex Sans",sans-serif; padding:7px 11px;
  cursor:pointer}}
.tab[aria-pressed="true"]{{background:var(--turf); border-color:var(--turf); color:#fff}}
.tab:focus-visible{{outline:2px solid var(--turf); outline-offset:2px}}
.note{{font-size:12.5px; color:var(--ink-soft); line-height:1.55; max-width:74ch;
  border-left:2px solid var(--turf); padding:2px 0 2px 12px; margin:16px 0}}
.pane{{margin-top:14px}}
.blurb{{font-size:13px; color:var(--ink-soft); margin:0 0 10px}}
iframe{{width:100%; height:760px; border:1px solid var(--rule); background:var(--panel)}}
img{{max-width:100%; border:1px solid var(--rule); background:var(--panel)}}
.open{{font-size:12.5px; margin:10px 0 0}}
.open a, .sub a{{color:var(--turf)}}
</style>

<div class="wrap">
  {NAV.replace('<a href="charts.html" data-page="charts">', '<a href="charts.html" data-page="charts" aria-current="page">')}
  <h1>Two views of the same five seasons</h1>
  <p class="sub"><b>Average vs share</b> plots the conventional measure against the
  pitch-normalised one; <b>rank by season</b> tracks the three best batters on median share
  over time. Each is drawn by all six plotting libraries from one shared dataset.
  Division 1 specialist batters, 2022&ndash;2026, minimum 12 innings in a season.
  The horizontal axis is the conventional batting average; the vertical axis is the median
  share of all runs scored in the match. The quadrants split at the field medians, so the
  off-diagonal corners are the interesting ones: high average with a low share means the runs
  came when runs were cheap. Numbers 8&ndash;11 are excluded rather than clipped, which keeps
  poor top-order batters visible in the bottom-left.</p>

  <div class="controls">
    <div class="group"><span class="lab">Chart</span>
      <button class="tab" data-chart="scatter" aria-pressed="true">Average vs share</button>
      <button class="tab" data-chart="ranks">Rank by season</button></div>
    <div class="group"><span class="lab">Library</span>{tabs_lib}</div>
    <div class="group" id="modegroup"><span class="lab">Colour by</span>{tabs_mode}</div>
  </div>
  <p class="note" id="modenote"></p>
  {''.join(panes)}
</div>

<script>
const NOTES = {json.dumps(MODE_NOTE)};
const RANK_NOTE = {json.dumps(RANK_NOTE)};
let lib = "plotly", mode = "performers", chart = "scatter";
function show() {{
  document.querySelectorAll('.pane').forEach(p => {{
    p.hidden = !(p.dataset.lib === lib && p.dataset.chart === chart &&
                 (chart === "ranks" || p.dataset.mode === mode));
  }});
  document.getElementById('modegroup').hidden = chart !== "scatter";
  document.querySelectorAll('.tab[data-chart]').forEach(b =>
    b.setAttribute('aria-pressed', b.dataset.chart === chart));
  document.querySelectorAll('[data-lib]').forEach(b => {{
    if (b.classList.contains('tab')) b.setAttribute('aria-pressed', b.dataset.lib === lib);
  }});
  document.querySelectorAll('[data-mode]').forEach(b => {{
    if (b.classList.contains('tab')) b.setAttribute('aria-pressed', b.dataset.mode === mode);
  }});
  document.getElementById('modenote').textContent =
    chart === "ranks" ? RANK_NOTE : NOTES[mode];
}}
document.querySelectorAll('.tab[data-lib]').forEach(b =>
  b.onclick = () => {{ lib = b.dataset.lib; show(); }});
document.querySelectorAll('.tab[data-mode]').forEach(b =>
  b.onclick = () => {{ mode = b.dataset.mode; show(); }});
document.querySelectorAll('.tab[data-chart]').forEach(b =>
  b.onclick = () => {{ chart = b.dataset.chart; show(); }});
show();
</script>
"""
    open(f"{SITE}/charts.html", "w").write(html + "\n</html>\n")
    return len(html)


DATA_FILES = [
    "player_rankings_div1_career.csv", "player_rankings_div2_career.csv",
    "player_rankings_div1_by_season.csv", "player_rankings_div2_by_season.csv",
    "scatter_data.csv", "rank_data.csv", "matches.csv",
]


def build_data():
    rows = []
    for f in DATA_FILES:
        shutil.copy(f, f"{SITE}/data/{f}")
        rows.append((f, os.path.getsize(f"{SITE}/data/{f}")))
    shutil.copy("innings_bat.csv", f"{SITE}/data/innings_bat.csv")
    rows.append(("innings_bat.csv", os.path.getsize(f"{SITE}/data/innings_bat.csv")))
    items = "\n".join(
        f'    <li><a href="{f}">{f}</a> <span>{s/1024:,.0f} KB · '
        f'{len(pd.read_csv(f"{SITE}/data/{f}")):,} rows</span></li>' for f, s in rows)
    open(f"{SITE}/data/index.html", "w").write(f"""{DOCTYPE}{HEAD}<title>Data Files</title>
<style>body{{font:14px/1.6 system-ui,sans-serif;max-width:680px;margin:40px auto;
padding:0 16px;background:#f4f5f0;color:#1b2620}}
a{{color:#3f6b4c}} li{{margin:6px 0}} span{{color:#5c6a62;font-size:12.5px}}
@media (prefers-color-scheme:dark){{body{{background:#121613;color:#e7ece7}}
a{{color:#7fbd92}} span{{color:#9daba2}}}}</style>
<h1>Data</h1>
<p>Everything behind the tables and charts, built from Cricsheet ball-by-ball data.</p>
<ul>
{items}
</ul>
<p><a href="../index.html">&larr; back</a></p>
""")
    return rows


GITIGNORE = """# the rebuild workspace: unpacked match files, the 24 MB Cricsheet zip,
# and the intermediate CSVs. Nothing in here belongs in the repository.
build/

__pycache__/
*.pyc
.venv/
"""

README = """# Share of Runs

Pitch-normalised batting metrics for the County Championship, built from
[Cricsheet](https://cricsheet.org/downloads/) ball-by-ball data (1,467 matches, 2014–2026).

Instead of a batting average, every measure here is a **share** or a **rank**: what
fraction of the match's runs a batter made, what fraction of his own side's, and how
often he finished first or in the top three among his team's scorers. That puts a
season on a Taunton road and a season on a Chelmsford green-top on the same scale.

## Pages

| Page | What it is |
|---|---|
| `index.html` | Full interactive rankings table — both divisions, every season or career, filterable by position and qualification |
| `charts.html` | Batting average against median % of match runs, six panels (five seasons + combined) × three colourings × six plotting libraries |
| `data/` | The CSVs behind all of it |

## Publishing to GitHub Pages

```bash
git init && git add . && git commit -m "Share of runs"
git branch -M main
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
```

Then in the repository: **Settings → Pages → Source: Deploy from a branch**, branch
`main`, folder `/ (root)` if you push the contents of `site/`, or `/docs` if you rename
`site/` to `docs/` and push the whole project.

The site is fully static — no build step, no dependencies. `.nojekyll` is included so
GitHub serves every file as-is.

## Rebuilding

One command. It downloads the current Cricsheet archive, rebuilds everything and
copies the finished site over the repository root:

```bash
./scripts/rebuild.sh
```

| | |
|---|---|
| `--force` | re-run the ETL even if the archive is unchanged |
| `--zip FILE` | use a local archive instead of downloading |
| `--workdir DIR` | working folder (default `./build`) |

If the downloaded archive is byte-identical to the last build's, the ETL is
skipped and the existing `innings_bat.csv` / `matches.csv` are reused — so a
re-run when Cricsheet has published nothing new costs seconds rather than
minutes. The script prints the archive's match count and the latest match date
in the data, which is how you tell whether new rounds have landed.

The ~830 MB of unpacked match JSONs are deleted once the ETL has consumed them.
The 24 MB zip is kept, so re-runs need no download and the exact snapshot a build
came from stays on disk.

### Python environment

The scripts need pandas, matplotlib, seaborn, plotnine, plotly, altair and bokeh.
They are **not** in a system Python by default — `scripts/requirements.txt` lists
them. With [uv](https://docs.astral.sh/uv/) installed there is nothing to set up:
each step runs via `uv run --with-requirements`, an ephemeral environment with
nothing to create or activate.

Without uv, make a virtual environment first and the scripts will use it:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
./scripts/rebuild.sh
```

### Running a single step

`scripts/_run.sh` runs one script in the same environment, from the working
folder:

```bash
cd build && ../scripts/_run.sh cch_metrics.py --division 2 --min-innings 30
```

The pipeline in order: `cch_etl.py` (JSON → `matches.csv`, `innings_bat.csv`),
`cch_metrics.py` per division, `chart_common.py` (`scatter_data.csv`),
`charts_static.py`, `charts_interactive.py`, `charts_ranks.py`, `site_build.py`.

## Notes on method

- **Home grounds** are inferred from the venue each county appears at; all 44 grounds
  resolve to a single county.
- **Batting position** comes from arrival at the crease, registering striker and
  non-striker together, so an opener who does not take strike still reads as 2.
- **Players** are keyed on Cricsheet registry IDs, not names.
- Aggregates reconcile exactly with the published 2025 Division 1 leading run scorers.
- 2026 is complete only to 15 September; Cricsheet had not yet published the closing
  rounds when this was built.
"""


if __name__ == "__main__":
    n1 = build_index()
    n2 = build_charts()
    rows = build_data()
    open(f"{SITE}/README.md", "w").write(README)
    open(f"{SITE}/.nojekyll", "w").write("")
    open(f"{SITE}/.gitignore", "w").write(GITIGNORE)
    print(f"index.html {n1/1024:,.0f} KB · charts.html {n2/1024:,.0f} KB")
    print("data:", ", ".join(f for f, _ in rows))
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(SITE) for f in fs)
    print(f"site total {total/1024/1024:.1f} MB")
