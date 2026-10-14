---
name: zen-ingest
description: Condense vault files into the Claude-maintained wiki under vault/90_wiki — one file per run, marking contradictions instead of overwriting. Also resolves conflicts with --resolve.
---

Arguments: $ARGUMENTS — either vault paths, or nothing (= work the "wiki behind" and "never-ingested" queues from vault/INDEX.md Health), or `--resolve <#c-id> "<decision>"`.

## Ingest

Read `vault/90_wiki/SCHEMA.md` first and follow its procedure exactly. For each input file, in order:
1. Immediately before dispatching, re-read `vault/90_wiki/INDEX.md`. Dispatch a fresh subagent with: the full `SCHEMA.md` text, the current text of `vault/90_wiki/INDEX.md` just read (not a path, not a copy read earlier), the input file path, and the instruction to perform steps 2–7 of the ingest procedure for that one file. The subagent returns: pages created, pages updated, conflict ids raised, or an error.
2. Stop if a subagent reports an error or that it could not complete any step; report what was done so far.

After all files: run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). Report pages created/updated and every new conflict id with its pages.

## Resolve

0. If no decision text is given, stop and ask; never resolve on your own judgement.
1. Find every page containing `#c-<id>` (grep `vault/90_wiki/`).
2. On each, rewrite the block to `— resolved`, set `Decision:` to the given text, and adjust the surrounding page text to reflect the decision. Do not delete either original claim line.
3. Append a `resolve` entry to `LOG.md` per SCHEMA.md. Update `updated` on each touched page.
4. Run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). Report the pages changed.
