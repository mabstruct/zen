---
name: zen-note
description: Create a new note in the ZEN vault from the template, with timestamps, filed into a cluster.
---

Arguments: $ARGUMENTS — a title, optional `--cluster <id>`, optional `--daily` for today's daily note.

1. `--daily`: path is `vault/01_daily/YYYY-MM-DD.md` from `02_templates/daily.md`; title is the date. If it exists, open it instead. Keep the template's `tags: [daily]` and layout; fill `title` with the date and `created`/`updated` as in step 3.
2. Otherwise: ask for the cluster if not given (list `vault/1x_*`). Path is `vault/<cluster>/<slug-of-title>.md` from `02_templates/note.md`. If it exists, stop and say so.
3. For a non-daily note: fill `title`, `created` and `updated` with the current ISO 8601 time with offset (`date +%Y-%m-%dT%H:%M:%S%z` then insert the colon in the offset), `tags: []`, and the `# <title>` heading.
4. If the user gave body text, add it. Run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). Report the path.
