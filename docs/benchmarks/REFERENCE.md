# Reference document

`vault/15_cosmology/sample-seventh.md` — Chapter 7, "Seventh rung: the Milky Way", from a book on the cosmic distance ladder. Original: `vault/15_cosmology/_originals/sample-seventh.pdf` (42 pages, 59.5 MB, image-heavy). Extracted text: 128 KB, 20.8k words, ~1,900 lines, ~30k tokens; negligible extraction noise.

Use it as the fixed input for every ingest comparison and timing measurement, so results stay comparable across models, SCHEMA changes and skill changes.

Baseline (2026-10-15): first ingest by Fable 5.1 — 5 min 58 s, 159k subagent tokens, 14 tool calls, 24 pages (1 source, 8 topics, 15 entities), 6,112 body words. Sonnet 5.5 on an identical copy — 2 min 36 s, 138k tokens, same 24 pages, 4,335 words. Full comparison: [2026-10-15-ingest-model-comparison.md](2026-10-15-ingest-model-comparison.md). The trust test ([../tests/trust-test.md](../tests/trust-test.md)) is built on this document's wiki pages.
