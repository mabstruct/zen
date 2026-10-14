# Trust test

Purpose: prove the wiki marks contradictions instead of overwriting, and merges harmless confirmations (spec §11).

Precondition: met. The first ingest of `10_ai/1706.03762.md` already produced `vault/90_wiki/topics/attention-mechanism.md`, `topics/multi-head-attention.md`, `topics/transformer-architecture.md`, `entities/transformer.md` and `sources/1706.03762.md`. Pick claims from these pages.

1. Pick three concrete claims from those wiki pages, plus one more claim for the harmless restatement. Fill in the table.

   | # | claim (verbatim) | page path | contradicting bullet (what you will write) |
   |---|------------------|-----------|--------------------------------------------|
   | 1 | | | |
   | 2 | | | |
   | 3 | | | |
   | 4 (restatement) | | | |

2. Create `vault/00_inbox/trust-test.md`:

   ```markdown
   ---
   title: Trust test note
   type: note
   cluster: 10_ai
   tags: [trust-test]
   ---

   - (bullet 1)
   - (bullet 2)
   - (bullet 3)
   - (bullet 4)
   ```

   Bullet N of the note contradicts claim N; bullet 4 restates row 4 word for word.
3. Run `/zen-intake` with no arguments (inbox mode; the note's `cluster:` key files it — the skill will not ask for a cluster). Expected: it reports `filed` and the note is now at `vault/10_ai/trust-test.md`. Then `/zen-ingest 10_ai/trust-test.md`.
4. Check:
   - [ ] three conflict blocks with three distinct ids exist; each appears on every page where the claim lives
   - [ ] both claim lines are present in each block, with sources and captured dates
   - [ ] no earlier statement was deleted or rewritten (`git diff vault/90_wiki`)
   - [ ] the harmless bullet was merged, with the note added as a source, and raised no conflict
   - [ ] `LOG.md` has the run with the ids; `vault/INDEX.md` Health lists the open conflicts
5. Resolve one: `/zen-ingest --resolve #c-NNNN "original claim holds; test note is wrong"`. Check the block is `resolved` on every page, the decision is logged, Health count drops by one.
6. Record the outcome and date below. Keep `vault/10_ai/trust-test.md`; removing it would leave dead source links in the wiki. Resolve the other two conflicts the same way, or leave them open as worked examples — record which in the Runs row.

## Runs

| date | result | notes |
|------|--------|-------|
