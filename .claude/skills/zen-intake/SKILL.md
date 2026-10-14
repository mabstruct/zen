---
name: zen-intake
description: File a document, URL, arXiv paper or DOI into the ZEN vault (original + markdown companion), or process everything in vault/00_inbox. No AI involved; deterministic.
---

Arguments: $ARGUMENTS — zero or more specs (path, URL, arXiv id/URL, DOI), optional `--cluster <id>`.

1. If no `--cluster` was given and specs are present, ask which cluster (list the `vault/1x_*` folders). Do not guess.
2. Run `(cd tools && uv run zen-intake <specs> --cluster <id> --vault ../vault)`. Omit specs to process the inbox; omit `--cluster` when none was given (inbox mode processes `00_inbox/`).
3. Run `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`).
4. Report the intake summary verbatim and the Health section. Anything left in the inbox or failed: say what and why.
