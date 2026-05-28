#!/usr/bin/env bash
# audit_harness.sh — wraps the replay/check cycle.
#
# Usage:
#   ./audit_harness.sh <harness-slug> <provider> [model]
#
# Expects a captured request body at:
#   examples/<harness-slug>-req.json
# Produces a verdict to stdout and writes:
#   examples/<harness-slug>-report.json

set -euo pipefail

slug="${1:?usage: $0 <slug> <provider> [model]}"
provider="${2:?usage: $0 <slug> <provider> [model]}"

root="$(cd "$(dirname "$0")/.." && pwd)"
req="$root/examples/$slug-req.json"
out="$root/examples/$slug-report.json"

if [[ ! -f "$req" ]]; then
  echo "missing request body: $req" >&2
  echo "see tools/replay_harness.md for how to capture it" >&2
  exit 1
fi

python3 "$root/tools/check_cache.py" --provider "$provider" --body "$req" > "$out"
echo "report written: $out"
cat "$out"
