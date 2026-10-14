#!/usr/bin/env bash
# Re-index and re-embed after vault changes. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
qmd update
qmd embed
qmd cleanup
