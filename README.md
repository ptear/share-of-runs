# Share of Runs

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
