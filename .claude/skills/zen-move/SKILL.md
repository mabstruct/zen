---
name: zen-move
description: Move a note or companion (and its original) from one cluster to another after a wrong filing decision, rewriting every link and wiki reference. Deterministic, no AI.
---

Arguments: $ARGUMENTS — a vault-relative path (e.g. `15_era/sample-seventh.md`) and `--cluster <id>`; or `--rename-cluster <old> <new>` to rename a whole cluster.

1. If no `--cluster` was given, ask which cluster (list the `vault/1x_*` folders). Do not guess.
2. Run `(cd tools && uv run zen-move <path> --cluster <id> --vault ../vault --dry-run)` and show the plan.
3. Run it without `--dry-run`. It moves the file and its original, rewrites inbound links and wiki `sources:` entries, logs a `move` entry, and re-indexes. It refuses — and rolls back — if the move would add a broken link.
4. Run `./scripts/qmd-refresh.sh` (from the `zen/` directory).
5. Report the tool's one-line result. A move never changes `updated`, so nothing enters the wiki-behind queue.

Renaming a whole cluster: `(cd tools && uv run zen-move --rename-cluster <old> <new> --vault ../vault [--dry-run])`. Links inside the cluster are relative and stay as they are; links from other clusters and the wiki, and wiki `sources:` entries, are rewritten; one `move <old> → <new>` LOG entry is written. Same refusal and rollback rules. Then refresh qmd.
