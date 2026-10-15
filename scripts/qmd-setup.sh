#!/usr/bin/env bash
# One-time qmd setup for the ZEN vault. Idempotent. Run from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v qmd >/dev/null 2>&1 || npm install -g @tobilu/qmd
[ -f .qmd/index.yml ] || qmd init

if ! qmd collection list 2>/dev/null | grep -qE '(^|\s)zen(\s|$)'; then
  qmd collection add "$PWD/vault" --name zen --mask "**/*.md"
fi

# ignore patterns are YAML-only (no CLI flag) — merge them into .qmd/index.yml
uv run --project tools python - <<'PY'
import yaml, pathlib
p = pathlib.Path(".qmd/index.yml")
cfg = yaml.safe_load(p.read_text()) or {}
col = cfg.setdefault("collections", {}).setdefault("zen", {})
want = ["_meta/**", "**/_originals/**", "02_templates/**", "INDEX.md", "**/_cluster.md", "90_wiki/SCHEMA.md", "90_wiki/LOG.md"]
col["ignore"] = sorted(set(col.get("ignore", [])) | set(want))
p.write_text(yaml.safe_dump(cfg, sort_keys=False))
print("ignore:", col["ignore"])
PY

if ! qmd context list | grep -qF '/ (root)'; then
  qmd context add qmd://zen "ZEN personal knowledge vault. Notes, document companions (markdown twins of PDFs/articles with extracted text), and a Claude-maintained wiki under 90_wiki. Clusters: 10_ai, 11_research, 12_mabstruct, 13_personal, 14_reading, 15_cosmology."
fi
if ! qmd context list | grep -qE '^ +90_wiki$'; then
  qmd context add qmd://zen/90_wiki "Condensed, cross-linked knowledge maintained by Claude. Prefer these pages over raw sources."
fi

qmd pull
qmd update
qmd embed
qmd status
