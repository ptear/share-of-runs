#!/usr/bin/env bash
# Run one pipeline step in the right Python environment.
# Used by rebuild.sh; also usable on its own:  ./scripts/_run.sh cch_metrics.py --division 2
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "── $*" >&2   # progress goes to stderr so callers can capture stdout
if command -v uv >/dev/null 2>&1; then
  # ephemeral environment from requirements.txt — nothing to create or activate
  exec uv run --quiet --with-requirements "$HERE/requirements.txt" python "$@"
else
  # fall back to whatever python3 is active (your own venv)
  exec python3 "$@"
fi
