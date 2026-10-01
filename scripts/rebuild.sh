#!/usr/bin/env bash
# Rebuild the whole site from the latest Cricsheet archive.
#
#   ./scripts/rebuild.sh                 download; rebuild only if the archive changed
#   ./scripts/rebuild.sh --charts        skip the ETL, re-render charts and site
#                                        (what you want after a code change)
#   ./scripts/rebuild.sh --force         re-run everything including the ETL
#   ./scripts/rebuild.sh --zip FILE      use a local archive instead of downloading
#   ./scripts/rebuild.sh --workdir DIR   working folder (default: ./build)
#
# The ~830 MB of unpacked match JSONs are deleted once the ETL has consumed them;
# the 24 MB zip is kept, so a re-run needs no download and the exact snapshot a
# build came from stays on disk.
set -euo pipefail

URL="https://cricsheet.org/downloads/cch_male_json.zip"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
WORK="$ROOT/build"
FORCE=0
CHARTS=0
LOCAL_ZIP=""

while [ $# -gt 0 ]; do
  case "$1" in
    --force)   FORCE=1; shift ;;
    --charts)  CHARTS=1; shift ;;
    --zip)     LOCAL_ZIP="$2"; shift 2 ;;
    --workdir) WORK="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
done

mkdir -p "$WORK"
cd "$WORK"
ZIP="$WORK/cch_male_json.zip"
STAMP="$WORK/.archive.sha"

# ---------------------------------------------------------------- 1. get the archive
if [ -n "$LOCAL_ZIP" ]; then
  echo "── using local archive $LOCAL_ZIP"
  cp "$LOCAL_ZIP" "$ZIP"
else
  echo "── downloading $URL"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --progress-bar -o "$ZIP.part" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -q --show-progress -O "$ZIP.part" "$URL"
  else
    echo "need curl or wget (or pass --zip FILE)"; exit 1
  fi
  mv "$ZIP.part" "$ZIP"
fi

SHA="$(sha256sum "$ZIP" | cut -d' ' -f1)"
MATCHES="$(unzip -p "$ZIP" README.txt 2>/dev/null | grep -o '[0-9,]* County Championship matches' || echo 'unknown match count')"
echo "   archive: $MATCHES"

# ---------------------------------------------------------------- 2. ETL, if it changed
UNCHANGED=0
if [ -f "$STAMP" ] && [ "$SHA" = "$(cat "$STAMP")" ] \
   && [ -f innings_bat.csv ] && [ -f matches.csv ]; then UNCHANGED=1; fi

if [ "$UNCHANGED" -eq 1 ] && [ "$FORCE" -eq 0 ] && [ "$CHARTS" -eq 0 ]; then
  echo "── archive unchanged since the last build — nothing to do."
  echo "   --charts re-renders from the existing data (after a code change)"
  echo "   --force  re-runs the ETL as well"
  exit 0
fi

if [ "$UNCHANGED" -eq 1 ] && [ "$FORCE" -eq 0 ]; then
  echo "── archive unchanged; reusing innings_bat.csv / matches.csv"
else
  echo "── unpacking and running the ETL"
  rm -f [0-9]*.json                  # stale match files would be picked up by the glob
  unzip -q -o "$ZIP"
  cp "$HERE"/*.py "$HERE/page_template.html" "$WORK/"
  "$HERE/_run.sh" cch_etl.py
  echo "── removing $(ls [0-9]*.json | wc -l) unpacked match files (the zip is kept)"
  rm -f [0-9]*.json
  echo "$SHA" > "$STAMP"
fi

echo "   latest match date in the data: $(
  python3 - <<'PY' 2>/dev/null || echo unknown
import csv
print(max(r["date"] for r in csv.DictReader(open("matches.csv"))))
PY
)"

# ---------------------------------------------------------------- 3. metrics, charts, site
cp "$HERE"/*.py "$HERE/page_template.html" "$WORK/"
R="$HERE/_run.sh"
"$R" cch_metrics.py --division 1 --min-innings 40 --min-innings-season 6
"$R" cch_metrics.py --division 2 --min-innings 40 --min-innings-season 6
"$R" chart_common.py
"$R" charts_static.py
"$R" charts_interactive.py
"$R" charts_ranks.py
"$R" site_build.py

# ---------------------------------------------------------------- 4. publish
echo "── copying $WORK/site -> $ROOT"
cp -r "$WORK/site/." "$ROOT/"
cp "$WORK"/*.csv "$ROOT/data/" 2>/dev/null || true

echo
echo "Done. Review with:  git -C \"$ROOT\" status"
echo "Then:               git -C \"$ROOT\" add -A && git -C \"$ROOT\" commit -m 'rebuild' && git -C \"$ROOT\" push"
