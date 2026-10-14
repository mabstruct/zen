# ZEN — rules for Claude

ZEN is a personal knowledge system. `vault/` is the only truth: markdown notes, companions (markdown twins of original documents in `_originals/`), and a wiki Claude maintains. Everything else is derived and disposable.

## Brain-First ladder — every knowledge question, in this order

Before step 1, run `cd tools && uv run zen-index --check --vault ../vault`; if it exits 1, run `uv run zen-index --vault ../vault` first.

1. Read `vault/INDEX.md`. If the source is listed, open exactly that file.
2. Check the wiki via `vault/90_wiki/INDEX.md`. Prefer a wiki page over raw sources; the knowledge may already be condensed.
3. Only then search: `qmd query "<question>" -n 8` (run from the `zen/` directory). Judge candidates by their snippets. Do not open files to decide.
4. Open exactly ONE file — the best — and read only the relevant section. In a companion read `## Summary` first; `## Extracted text` only if the summary does not answer.
5. Answer, citing vault paths. Never scan folders. Never open `_originals/`.

## Never

- Hand-edit `vault/INDEX.md`, `vault/_meta/`, or anything under `vault/90_wiki/`. The wiki changes only through `/zen-ingest`.
- Move or rename vault files by hand; use `/zen-intake`, `/zen-note`.
- Decide a conflict. Mark it; the human decides.

## After writing to the vault

Run `cd tools && uv run zen-index --vault ../vault` and, from the `zen/` directory, `./scripts/qmd-refresh.sh`. The skills do this for you.

## Skills

`/zen-ask`, `/zen-intake`, `/zen-ingest`, `/zen-index`, `/zen-note` — see `.claude/skills/`. Wiki rules: `vault/90_wiki/SCHEMA.md`.

## Conventions

Frontmatter on every note: `title`, `type`, `created`, `updated`, `tags` (ISO 8601 timestamps with offset). Cluster = folder (`1x_<name>`), never a frontmatter field. Standard relative markdown links. One note, one place.
