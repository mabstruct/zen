---
name: zen-intake
description: File a document, URL, arXiv paper or DOI into the ZEN vault (original + markdown companion), or process everything in vault/00_inbox. No AI involved; deterministic.
---

Arguments: $ARGUMENTS — zero or more specs (path, URL, arXiv id/URL, DOI), optional `--cluster <id>`; or `--retry-missing`; or `--recapture <vault-path>`.

1. If no `--cluster` was given and specs are present, ask which cluster (list the `vault/1x_*` folders). Do not guess.
2. Convert every file or folder spec to an absolute path first (`realpath`), because the tool runs with `tools/` as its working directory.
3. Run `(cd tools && uv run zen-intake <specs> --cluster <id> --vault ../vault)`. Omit specs to process the inbox; omit `--cluster` when none was given (inbox mode processes `00_inbox/`).
4. Run `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`).
5. Report the intake summary verbatim and the Health section. Anything left in the inbox or failed: say what and why.

## Refreshing existing companions

- `--retry-missing`: `(cd tools && uv run zen-intake --retry-missing --vault ../vault)` re-fetches every companion with `snapshot: missing` and fills it in place (`refreshed`), or leaves it as is (`still-missing`).
- `--recapture <vault-path>`: `(cd tools && uv run zen-intake --recapture <vault-path> --vault ../vault)` re-fetches one companion's `source.url`. `unchanged` = same content, nothing touched. `refreshed` = new snapshot, new `captured`, `## Summary` cleared; the earlier snapshot stays in the workspace's git history.

Both keep the companion's path and `created`, bump `updated`, and refuse with `duplicate` if the new content already belongs to another companion. Afterwards run `./scripts/qmd-refresh.sh`. A refreshed companion that was ingested before now shows under wiki-behind; tell the user to run `/zen-ingest` on it (it routes to the deep ingester as a re-ingest).
