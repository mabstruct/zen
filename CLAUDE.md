# ZEN — rules for Claude

ZEN is a personal knowledge system. `vault/` is the only truth: markdown notes, companions (markdown twins of original documents in `_originals/`), and a wiki Claude maintains. Everything else is derived and disposable.

## Brain-First ladder — every knowledge question, in this order

`(cd tools && uv run zen-ask-prep --vault ../vault "<question>")` performs steps 0–3 below in one call (stale check and re-index, both index files, qmd hits with snippets); use it instead of running them separately — the rules are unchanged, only the number of round trips. Without it, before step 1 run `(cd tools && uv run zen-index --check --vault ../vault)`; if it exits 1, run `(cd tools && uv run zen-index --vault ../vault)` first.

1. Read `vault/INDEX.md`. If the source is listed, open exactly that file. If both a wiki page and a raw file are listed for the answer, open the wiki page.
2. Check the wiki via `vault/90_wiki/INDEX.md`. Prefer a wiki page over raw sources; the knowledge may already be condensed.
3. Only then search: `qmd query "<question>" -n 8` (run from the `zen/` directory). Judge candidates by their snippets. Do not open files to decide.
4. Open exactly ONE file — the best — and read only the relevant section. In a companion read `## Summary` first; `## Extracted text` only if the summary does not answer.
5. Answer, citing vault paths. Never scan folders. Never open `_originals/`.

## Never

- Hand-edit `vault/INDEX.md`, `vault/_meta/`, or anything under `vault/90_wiki/`. The wiki changes only through `/zen-ingest`.
- Move or rename vault files by hand; use `/zen-intake`, `/zen-note`.
- Decide a conflict. Mark it; the human decides.

## After writing to the vault

Run `(cd tools && uv run zen-index --vault ../vault)`, then `./scripts/qmd-refresh.sh` (run from the `zen/` directory; it works from any cwd but keep the session at `zen/`). The skills do this for you.

## Skills

`/zen-ask`, `/zen-intake`, `/zen-ingest`, `/zen-index`, `/zen-note` — see `.claude/skills/`. Wiki rules: `vault/90_wiki/SCHEMA.md`.

## Model baseline

Tokens are spent in two places only. The baseline comes from `docs/benchmarks/2026-10-15-ingest-model-comparison.md`; change it by editing the `model:` line of the agent file.

| task | runs on | why |
|------|---------|-----|
| `/zen-ingest`, routine first ingest | `.claude/agents/zen-ingester.md` (mid-tier) | matched the premium model on accuracy at half the time; its gaps are omissions, and the companion keeps the full text |
| `/zen-ingest`, deep: extracted text > 50 KB, re-ingest, synthesis, or `--deep` | `.claude/agents/zen-ingester-deep.md` (premium) | depth, numbers, dense cross-links; conflict detection gets harder as the wiki grows |
| `/zen-ingest --model <name>` | that model, this run only | one-off override |
| `/zen-ask` | the session model (`/model`) | small context, interactive |
| intake, index, note | no model | deterministic |

## Conventions

Frontmatter on every note: `title`, `type`, `created`, `updated`, `tags` (ISO 8601 timestamps with offset). Cluster = folder (`1x_<name>`), never a frontmatter field. Standard relative markdown links. One note, one place.
