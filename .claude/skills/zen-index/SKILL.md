---
name: zen-index
description: Rebuild vault/INDEX.md and _meta/map.json, refresh qmd, and show the vault Health section.
---

1. `(cd tools && uv run zen-index --vault ../vault)`
2. `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`)
3. Show the header line and the full `## Health` section. For each health kind present, one sentence on what to do about it.
