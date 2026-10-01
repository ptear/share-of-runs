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
