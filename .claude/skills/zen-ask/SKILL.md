---
name: zen-ask
description: Answer a knowledge question from the ZEN vault using the Brain-First ladder. Use for any "what do I know about…", "where did I read…", "what does X say about Y" question.
---

Question: $ARGUMENTS

Three calls, no more: prep, one file, answer.

1. Run `(cd tools && uv run zen-ask-prep --vault ../vault "<question>")`. One call performs ladder steps 0–3: it re-indexes if stale, then prints `vault/INDEX.md`, `vault/90_wiki/INDEX.md`, and the top qmd hits with snippets. Do not run `zen-index`, read the index files, or run `qmd` separately.
2. Walk the ladder over that output, in order, and pick exactly ONE file:
   - INDEX.md: if a listed file obviously holds the answer, that is your file. If both a wiki page and a raw file are listed for the answer, take the wiki page.
   - Wiki INDEX.md: if a wiki page matches, that is your file.
   - qmd hits: otherwise pick the single best candidate from the snippets. Do not open others.
3. Open that one file. Companion: read `## Summary`; read `## Extracted text` only if the summary does not answer.
4. Answer in a few sentences. Cite every vault path you used. If nothing answers, say so and list the two closest candidates — do not widen the search.
