# Wiki schema — Claude's work instruction

Read this before every wiki operation. Humans never edit this folder; only `/zen-ingest` writes here.

## Page types and folders

| type | folder | one page per | content |
|------|--------|--------------|---------|
| wiki-source | sources/ | ingested vault file | what it claims, 10–20 lines; key terms; link back to the vault file |
| wiki-topic | topics/ | concept | condensed knowledge across sources; sections: Summary, Claims (each with source), Open questions, Related |
| wiki-entity | entities/ | person, project, tool, organisation | what it is, why it matters here, links to topics and sources |
| wiki-synthesis | syntheses/ | theme where ≥ 3 sources converge | argument across topics; written only when the threshold is met |

Filenames: a `sources/` page is named after the input's vault filename stem, e.g. input `10_ai/1706.03762.md` → `sources/1706.03762.md`. `topics/`, `entities/` and `syntheses/` pages use the slug of their own title (§4 slug rules: lowercase ASCII, hyphens), e.g. `topics/attention-mechanism.md`.

Frontmatter (`tags` optional):

```yaml
---
title: Attention mechanism
type: wiki-topic
created: 2026-10-15T09:10:00+02:00
updated: 2026-10-15T09:10:00+02:00
sources: [10_ai/1706.03762.md]
confidence: medium   # low = 1 source, medium = 2–3 agreeing, high = ≥ 4 agreeing
tags: []
---
```

## Citations and links

Every claim on a topic, entity or synthesis page ends with a relative markdown link to its source page, in parentheses, with the source page's filename stem as link text. Example: a claim on `topics/attention-mechanism.md` taken from `sources/1706.03762.md` ends with ` (` + `[1706.03762]` + `(../sources/1706.03762.md)` + `)`, the four parts joined with nothing between them. (The parts are shown separately only so this file does not itself contain a link.) Links are always relative to the page that contains them.

## Ingest procedure (one file per run)

1. Read `SCHEMA.md` (this file) and `INDEX.md`.
2. Read the input file from the vault.
3. From `INDEX.md`, select the pages this file touches. Open only those.
4. Write or update: its `sources/` page; affected `topics/` and `entities/`; links in both directions (relative markdown links); a `syntheses/` page if ≥ 3 sources now converge.
5. For every claim you write, check the target page for an existing statement it contradicts. If so: add the new claim (B) to the page like any other claim (on topics: in Claims), with its own source link, so both claims stay readable there; and add a conflict block (below) with the earlier claim as A and the new one as B. **Never delete or rewrite the earlier statement.**
6. If the input's `## Summary` is empty, write 3–6 lines there. If the input is a companion whose `title` is a bare identifier (an arXiv id, a filename stem), set `title` and the `# ` heading to the document's real title from its text. Set `ingested` and `updated` on the input to the same ISO 8601 timestamp with offset (one value, used for both).
7. Append a run entry to `LOG.md`. Update `INDEX.md`: one line per page, under the heading of its type — a list item holding a markdown link to the page (title as link text, path relative to this folder), then ` · <type> · <updated as YYYY-MM-DD>`.

**Re-ingest.** When the input already has a `sources/` page (the wiki-behind queue), rewrite that source page from the current text and update every claim attributed to it on other pages to the new wording. A source never conflicts with its own earlier version; only disagreement with a different source is marked. The LOG entry says `re-ingest`.

## Conflict block

Place it on every page where the conflict is visible, with the same id. Ids are sequential; the next id is one more than the highest `#c-NNNN` in `LOG.md` (four digits, zero-padded: `#c-0001` if none).

```markdown
> [!conflict] #c-NNNN — open
> A: "<claim>" — <link to A's source page> (captured 2026-03-01)
> B: "<claim>" — <link to B's source page> (captured 2026-10-14)
> Decision: pending
```

Each `<link to … source page>` is a markdown link written exactly as in Citations: link text = the source page's filename stem, target relative to the page containing the block (from `topics/`: `../sources/1706.03762.md`). The `captured` date is the `YYYY-MM-DD` of that source's vault file `source.captured`; for a vault file without `captured` (a note), use its `created`.

Resolution (only via `/zen-ingest --resolve`): rewrite the block to `— resolved`, replace `Decision: pending` with the human's decision, update the page text to reflect it, and log it. Never resolve on your own judgement.

A statement that merely confirms an existing claim is not a conflict: merge it and add the source.

## LOG.md entry format

The heading word is `ingest`, or `re-ingest` for a re-ingest.

```markdown
## 2026-10-15T09:10:00+02:00 ingest 10_ai/1706.03762.md
- created: sources/1706.03762.md, topics/attention-mechanism.md
- updated: entities/transformer.md
- conflicts: #c-0003 (topics/attention-mechanism.md, entities/transformer.md)
```

```markdown
## 2026-10-16T08:00:00+02:00 resolve #c-0003
- decision: "<text>"
- pages: topics/attention-mechanism.md, entities/transformer.md
```
