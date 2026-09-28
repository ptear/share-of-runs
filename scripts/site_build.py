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


def build_index():
    frag = open("page_template.html").read()
    data = open("leaderboard.json").read()
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
    "performers": "The four players with more than one top-five composite finish since 2022 "
                  "are coloured; everyone else is grey. Marker shape shows batting position.",
    "position": "Coloured by the band holding most of a player's innings. The four performers "
                "keep a dark ring so they stay findable.",
    "team": "Coloured by county. Seventeen counties appear across the five seasons and no "
            "seventeen-colour scheme stays reliably separable — least of all for colourblind "
            "readers — so treat this as exploratory: identify points from the hover in the "
            "interactive versions rather than from the colour alone.",
}


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
                f'<section class="pane" data-lib="{lib}" data-mode="{mode}" hidden>'
                f'<p class="blurb"><b>{name}</b> — {blurb}</p>'
                f'{body}'
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
  <h1>Average against share of match runs</h1>
  <p class="sub">Division 1 specialist batters, 2022&ndash;2026, minimum 12 innings in a season.
  The horizontal axis is the conventional batting average; the vertical axis is the median
  share of all runs scored in the match. The quadrants split at the field medians, so the
  off-diagonal corners are the interesting ones: high average with a low share means the runs
  came when runs were cheap. Numbers 8&ndash;11 are excluded rather than clipped, which keeps
  poor top-order batters visible in the bottom-left.</p>

  <div class="controls">
    <div class="group"><span class="lab">Library</span>{tabs_lib}</div>
    <div class="group"><span class="lab">Colour by</span>{tabs_mode}</div>
  </div>
  <p class="note" id="modenote"></p>
  {''.join(panes)}
</div>

<script>
const NOTES = {json.dumps(MODE_NOTE)};
let lib = "plotly", mode = "performers";
function show() {{
  document.querySelectorAll('.pane').forEach(p => {{
    p.hidden = !(p.dataset.lib === lib && p.dataset.mode === mode);
  }});
  document.querySelectorAll('[data-lib]').forEach(b => {{
    if (b.classList.contains('tab')) b.setAttribute('aria-pressed', b.dataset.lib === lib);
  }});
  document.querySelectorAll('[data-mode]').forEach(b => {{
    if (b.classList.contains('tab')) b.setAttribute('aria-pressed', b.dataset.mode === mode);
  }});
  document.getElementById('modenote').textContent = NOTES[mode];
}}
document.querySelectorAll('.tab[data-lib]').forEach(b =>
  b.onclick = () => {{ lib = b.dataset.lib; show(); }});
document.querySelectorAll('.tab[data-mode]').forEach(b =>
  b.onclick = () => {{ mode = b.dataset.mode; show(); }});
show();
</script>
"""
    open(f"{SITE}/charts.html", "w").write(html + "\n</html>\n")
    return len(html)


DATA_FILES = [
    "player_rankings_div1_career.csv", "player_rankings_div2_career.csv",
    "player_rankings_div1_by_season.csv", "player_rankings_div2_by_season.csv",
    "scatter_data.csv", "matches.csv",
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

```bash
python3 cch_etl.py            # Cricsheet JSON  ->  matches.csv, innings_bat.csv
python3 cch_metrics.py --division 1 --min-innings 40 --min-innings-season 6
python3 cch_metrics.py --division 2 --min-innings 40 --min-innings-season 6
python3 chart_common.py       # scatter_data.csv
python3 charts_static.py      # matplotlib, seaborn, plotnine
python3 charts_interactive.py # plotly, altair, bokeh
python3 site_build.py         # assembles site/
```

Requires: pandas, matplotlib, seaborn, plotnine, plotly, altair, bokeh.

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
    print(f"index.html {n1/1024:,.0f} KB · charts.html {n2/1024:,.0f} KB")
    print("data:", ", ".join(f for f, _ in rows))
    total = sum(os.path.getsize(os.path.join(r, f))
                for r, _, fs in os.walk(SITE) for f in fs)
    print(f"site total {total/1024/1024:.1f} MB")
