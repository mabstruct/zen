#!/usr/bin/env bash
# Personal static export of the vault GUI. Run from zen/.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: scripts/ui-export.sh <folder> [--yes]" >&2; exit 2; }
folder="$(python3 -c 'import os,sys;print(os.path.abspath(sys.argv[1]))' "$1")"
cd "$(dirname "$0")/.."
(cd tools && uv run zen-index --vault ../vault)
(cd ui && npm ci --silent && node scripts/export.ts "$folder" "${@:2}")
