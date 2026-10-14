---
name: zen-ingest
description: Condense vault files into the Claude-maintained wiki under vault/90_wiki — one file per run, marking contradictions instead of overwriting. Also resolves conflicts with --resolve.
---

Arguments: $ARGUMENTS — either vault paths, or nothing (= work the "wiki behind" and "never-ingested" queues from vault/INDEX.md Health), or `--resolve <#c-id> "<decision>"`.

## Ingest

Read `vault/90_wiki/SCHEMA.md` first and follow its procedure exactly. For each input file, in order:
1. Dispatch a fresh subagent with: the SCHEMA.md text, `vault/90_wiki/INDEX.md`, the input file path, and the instruction to perform steps 2–7 of the ingest procedure for that one file and report created/updated pages and conflict ids.
2. Stop on the first error; report what was done so far.
After all files: run `cd tools && uv run zen-index --vault ../vault` and `./scripts/qmd-refresh.sh`. Report pages created/updated and every new conflict id with its pages.

## Resolve

1. Find every page containing `#c-<id>` (grep `vault/90_wiki/`).
2. On each, rewrite the block to `— resolved`, set `Decision:` to the given text, and adjust the surrounding page text to reflect the decision. Do not delete either original claim line.
3. Append a `resolve` entry to `LOG.md` per SCHEMA.md. Update `updated` on each touched page.
4. Run `cd tools && uv run zen-index --vault ../vault`. Report the pages changed.

Never resolve a conflict without an explicit decision in the arguments.
