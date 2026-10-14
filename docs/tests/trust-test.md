# Trust test

Purpose: prove the wiki marks contradictions instead of overwriting, and merges harmless confirmations (spec §11).

Precondition: met. The first ingest of `10_ai/1706.03762.md` already produced `vault/90_wiki/topics/attention-mechanism.md`, `topics/multi-head-attention.md`, `topics/transformer-architecture.md`, `entities/transformer.md` and `sources/1706.03762.md`. Pick claims from these pages.

1. Pick three concrete claims from those wiki pages (write them here with their page paths).
2. Create `vault/00_inbox/trust-test.md` with frontmatter `title: Trust test note`, `cluster: 10_ai`, and a body of four bullet points: three that contradict the chosen claims, one that restates a claim already in the wiki.
3. `/zen-intake` (files the note), then `/zen-ingest 10_ai/trust-test.md`.
4. Check:
   - [ ] three conflict blocks with three distinct ids exist; each appears on every page where the claim lives
   - [ ] both claim lines are present in each block, with sources and captured dates
   - [ ] no earlier statement was deleted or rewritten (`git diff vault/90_wiki`)
   - [ ] the harmless bullet was merged, with the note added as a source, and raised no conflict
   - [ ] `LOG.md` has the run with the ids; `vault/INDEX.md` Health lists the open conflicts
5. Resolve one: `/zen-ingest --resolve #c-NNNN "original claim holds; test note is wrong"`. Check the block is `resolved` on every page, the decision is logged, Health count drops by one.
6. Record the outcome and date below. Then `git rm vault/10_ai/trust-test.md`, `/zen-ingest --resolve` the other two the same way or leave them open as examples — your call, note it.

After the ingest, `./scripts/qmd-refresh.sh` from `zen/` refreshes search.

## Runs

| date | result | notes |
|------|--------|-------|
