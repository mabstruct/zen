---
name: zen-ingest
description: Condense vault files into the Claude-maintained wiki under vault/90_wiki — one file per run, marking contradictions instead of overwriting. Routes each file to the standard or deep model, and large files to a planned ingest (one planner, parallel page writers). Also resolves conflicts with --resolve.
---

Arguments: $ARGUMENTS — either vault paths, or nothing (= work the "wiki behind" and "never-ingested" queues from vault/INDEX.md Health), optionally `--deep`, `--model <name>`, `--single` (force the single-agent path), or `--resolve <#c-id> "<decision>"`.

## Ingest

Read `vault/90_wiki/SCHEMA.md` first. For each input file, in order:

1. **Choose the model** (model baseline, see CLAUDE.md):
   - `--model <name>` given → that model for this run.
   - `--deep` given, or the input's `## Extracted text` is larger than 50 KB, or the input already has a `sources/` page (a re-ingest) → deep.
   - otherwise → standard.
2. **Choose the path:** the extracted text is larger than 20 KB and `--single` was not given → planned path; otherwise → single-agent path.
   Say which model and path you chose and why, in one line.

### Single-agent path

3. Immediately before dispatching, re-read `vault/90_wiki/INDEX.md`. Dispatch one fresh subagent — `zen-ingester` (standard) or `zen-ingester-deep` (deep); pass `model` only for `--model` — with: the full `SCHEMA.md` text, the current text of `vault/90_wiki/INDEX.md` just read, the input file path, and the instruction to perform steps 2–7 of the ingest procedure for that one file. It returns pages created, pages updated, conflict ids raised, or an error.

### Planned path

3. Take one timestamp now (`date +%Y-%m-%dT%H:%M:%S%z`, colon inserted in the offset) — it is the run's `ingested` value. The plan path is the **absolute** path of `.ingest/<input stem>/plan.yaml` under `zen/` (`mkdir -p` its folder); use it as is in every command below.
4. **Plan.** Re-read `vault/90_wiki/INDEX.md`, then dispatch one `zen-ingest-planner` (standard) or `zen-ingest-planner-deep` (deep; pass `model` only for `--model`) with: the full `SCHEMA.md` text, the INDEX text just read, the input path, the plan path, and the timestamp. Wait for it. It returns the plan path, page counts and conflict ids — or an error.
5. **Check.** Run `(cd tools && uv run zen-plan check <plan path> --vault ../vault)`. If it does not print `plan ok`, stop and report the errors; write nothing.
6. **Write in parallel.** Run `(cd tools && uv run zen-plan batches <plan path> --size 6)`; each output line is one batch. Dispatch one `zen-page-writer` per batch **in the same message, in the background**, each with: the full `SCHEMA.md` text, the plan path, and its batch's page paths. Wait until all have reported. If any reports an error, stop: report which pages were written and which failed, keep the plan file, and do not run step 7.
7. **Finish.** Run `(cd tools && uv run zen-plan finish <plan path> --vault ../vault)` — it writes the source page, the companion's Summary/title/`ingested`, the LOG entry, and regenerates the wiki INDEX. Then delete `.ingest/<input stem>/`.

### After all files

Run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). Any broken link in Health after a planned run means a writer drifted from the plan — name it. Report pages created/updated, every new conflict id with its pages, which model and path handled each file, and the wall time of each run.

Stop at the first file whose ingest fails; report what was done so far.

## Resolve

0. If no decision text is given, stop and ask; never resolve on your own judgement.
1. Find every page containing `#c-<id>` (grep `vault/90_wiki/`).
2. On each, rewrite the block to `— resolved`, set `Decision:` to the given text, and adjust the surrounding page text to reflect the decision. Do not delete either original claim line.
3. Append a `resolve` entry to `LOG.md` per SCHEMA.md. Update `updated` on each touched page.
4. Run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). Report the pages changed.
