---
name: zen-ask
description: Answer a knowledge question from the ZEN vault using the Brain-First ladder. Use for any "what do I know about…", "where did I read…", "what does X say about Y" question.
---

Question: $ARGUMENTS

1. Run `(cd tools && uv run zen-index --check --vault ../vault)`. If it exits 1, run `(cd tools && uv run zen-index --vault ../vault)`.
2. Read `vault/INDEX.md`. If a listed file obviously holds the answer, open exactly that one and skip to step 6. If both a wiki page and a raw file are listed for the answer, open the wiki page.
3. Read `vault/90_wiki/INDEX.md`. If a wiki page matches, open exactly that page and skip to step 6.
4. Run `qmd query "<question>" -n 8` from the `zen/` directory. Pick the single best candidate from the snippets. Do not open others.
5. Open that one file. Companion: read `## Summary`; read `## Extracted text` only if the summary does not answer.
6. Answer in a few sentences. Cite every vault path you used. If nothing answers, say so and list the two closest candidates — do not widen the search.
