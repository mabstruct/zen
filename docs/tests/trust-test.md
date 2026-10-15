# Trust test

Purpose: prove the wiki marks contradictions instead of overwriting, and merges harmless confirmations (spec §11).

Reference document: `vault/15_cosmology/sample-seventh.md` (Chapter 7, "Seventh rung: the Milky Way"), ingested 2026-10-15 by Fable 5.1 into one source page, eight topics and fifteen entities. The independent review in [2026-10-15-ingest-model-comparison.md](../benchmarks/2026-10-15-ingest-model-comparison.md) found three factual slips in that ingest. This test plants the **correct** facts, so the three conflicts it raises are real and `--resolve` performs a genuine correction.

Precondition: met — the pages below exist.

1. The three claims and the restatement, taken verbatim from the live wiki:

   | # | claim (verbatim) | page path | contradicting bullet (what you will write) |
   |---|------------------|-----------|--------------------------------------------|
   | 1 | "Director of the Harvard Observatory (1846–1919) for over four decades after a decade teaching physics at MIT" | `vault/90_wiki/entities/edward-pickering.md` | 1846–1919 are Pickering's birth and death years (the chapter's figure caption), not his years as director; he became director after a decade teaching physics at MIT and held the post until his death in 1919. |
   | 2 | "Russell's 1913 Royal Astronomical Society paper gave the first chart resembling the modern diagram" — and, on the entity page, "Presented … to the Royal Astronomical Society in 1913, the first chart resembling the modern H–R diagram" | `vault/90_wiki/topics/hertzsprung-russell-diagram.md` and `vault/90_wiki/entities/henry-norris-russell.md` | Russell presented the paper to the Royal Astronomical Society in 1913, but the chart that first resembles the modern H–R diagram appeared in the paper published the following year, 1914. |
   | 3 | "plotted colour–magnitude diagrams of the Pleiades and Hyades (1910–1911), revealing the main sequence" | `vault/90_wiki/entities/ejnar-hertzsprung.md` | The first colour–magnitude diagram of Hertzsprung's results, for the Pleiades in 1910, was drawn by a colleague from Potsdam, not by Hertzsprung; Hertzsprung himself added the Hyades in 1911. |
   | 4 (restatement) | "Discovered axial precession by comparing his 850-star observations with the earlier catalogs of Eudoxus and Timocharis: Spica had shifted about 2 degrees toward the autumnal equinox in 150 years." | `vault/90_wiki/entities/hipparchus.md` | Hipparchus discovered axial precession by comparing his 850-star observations with the earlier catalogs of Eudoxus and Timocharis: Spica had shifted about 2 degrees toward the autumnal equinox in 150 years. |

   Claim 2 lives on two pages, so conflict 2 must appear on both with the same id. Claim 3 is already stated correctly on `topics/hertzsprung-russell-diagram.md` ("a Potsdam colleague drew the Pleiades diagram in 1910"), so conflict 3 must appear **only** on the Hertzsprung entity page; on the topic page the bullet is a confirmation, not a conflict.

2. Create `vault/00_inbox/trust-test.md` with exactly this content:

   ```markdown
   ---
   title: Trust test note
   type: note
   cluster: 15_cosmology
   tags: [trust-test]
   ---

   - 1846–1919 are Edward Pickering's birth and death years (the chapter's figure caption), not his years as director; he became Harvard Observatory director after a decade teaching physics at MIT and held the post until his death in 1919.
   - Russell presented "Relations Between the Spectra and Other Characteristics of the Stars" to the Royal Astronomical Society in 1913, but the chart that first resembles the modern H–R diagram appeared in the paper published the following year, 1914.
   - The first colour–magnitude diagram of Hertzsprung's results, for the Pleiades in 1910, was drawn by a colleague from Potsdam, not by Hertzsprung; Hertzsprung himself added the Hyades cluster in 1911.
   - Hipparchus discovered axial precession by comparing his 850-star observations with the earlier catalogs of Eudoxus and Timocharis: Spica had shifted about 2 degrees toward the autumnal equinox in 150 years.
   ```

   Bullet N contradicts claim N; bullet 4 restates row 4.

3. Run `/zen-intake` with no arguments (inbox mode; the note's `cluster:` key files it — the skill will not ask for a cluster). Expected: it reports `filed` and the note is now at `vault/15_cosmology/trust-test.md`. Then `/zen-ingest 15_cosmology/trust-test.md`.

4. Check:
   - [ ] three conflict blocks with three distinct ids exist: #1 on `entities/edward-pickering.md`; #2 on both `topics/hertzsprung-russell-diagram.md` and `entities/henry-norris-russell.md` with the same id; #3 on `entities/ejnar-hertzsprung.md` only
   - [ ] no conflict was raised on `topics/hertzsprung-russell-diagram.md` for the Pleiades statement — bullet 3 agrees with that page and must be merged there as a confirmation
   - [ ] both claim lines are present in each block, each with its source link and captured/created date
   - [ ] no earlier statement was deleted or rewritten (`git diff vault/90_wiki`)
   - [ ] bullet 4 was merged into `entities/hipparchus.md` with the note added as a source, and raised no conflict
   - [ ] `LOG.md` has the run with the ids; `vault/INDEX.md` Health lists three open conflicts

5. Resolve conflict 1 in favour of the note — this is a real correction: `/zen-ingest --resolve #c-NNNN "test note holds: 1846–1919 are birth and death years from a figure caption; Pickering was director until his death in 1919"`. Check: the block is `resolved` on the page, the page text now reflects the decision (no director year range), the decision is logged, Health count drops to two.

6. Record the outcome and date below. Keep `vault/15_cosmology/trust-test.md`; removing it would leave dead source links in the wiki. Resolve conflicts 2 and 3 the same way (both favour the note), or leave them open as worked examples — record which in the Runs row.

## Runs

| date | result | notes |
|------|--------|-------|
