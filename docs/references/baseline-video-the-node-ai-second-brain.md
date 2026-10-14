# Baseline reference: "Der echte Weg zum Second Brain" (The Node AI)

Source: https://www.youtube.com/watch?v=mHSOsy_usAg — The Node AI | AI Automation, 2026-07-19, 45 min, German.
Digest written 2026-10-14 from the full transcript. Role in ZEN: **the baseline** — ZEN follows this shape and deliberately deviates where noted in the ZEN spec.

Despite the title ("no coding, forget Obsidian"), the system *is* an Obsidian vault plus Claude Code. The point of the title: Obsidian is only the editor; the system lives in files and rules, and Claude types all code.

## The founding question

> How does collected knowledge become a system I can **trust**, instead of a growing junk pile?

Two halves:
1. **Findability** — find anything even when you only vaguely remember what it was about.
2. **Trust** — duplicates, contradictions, and stale versions must *surface*, not lie around silently.

Nothing in the question mentions a graph or nice views. Build the system that answers the question first; the UI is a window you build last.

## The four capabilities (written before any tool was chosen)

| # | Capability | Where it lives in the architecture |
|---|-----------|-----------------------------------|
| 1 | **Find** relevant info in seconds, even without the exact word → search must understand meaning | qmd (hybrid search) |
| 2 | **Read** what was found directly, in the same system, no app switch | web app / editor |
| 3 | **Stay clean** — detect contradictions, duplicates, stale states; *condense* knowledge instead of stacking it | LLM wiki (Karpathy pattern) |
| 4 | **Overview** — the whole system at a glance | graph view (last, not first) |

Constraint: knowledge base, index, graph and search run **fully local**. Only excerpts selected for analysis/wiki maintenance go to the model.

Advice: before installing anything, write your own 3–5 capabilities, each concrete enough to be verifiable.

## The process (six steps; four happen before any code)

1. **Order the data base** (no AI needed, most important). Re-structure the vault: workflow folders (Inbox, Daily Notes, Templates) + topic clusters (Content, Business, Community, Personal, Knowledge). Every note has exactly one place. "The best search in a chaos vault just finds your chaos faster."
2. **Brainstorm** — Claude asks questions one at a time (purpose, data base, must-do, must-NOT-do), proposes 2–3 approaches, human decides. Key decision made here: *work on the existing workspace as-is; no migration, no new format.* No code in this step.
3. **Spec** — design document, approved section by section. "The spec is the contract" — when a dispute arises during build, the spec rules, not memory or the AI's interpretation. ~30 min from first question to build start.
4. **Plan** — spec → small tasks (14 core tasks). Each task has a test and a concrete done-criterion ("search returns file X for question Y", not "build search").
5. **Build** task by task, fresh subagent per task with only the needed context, result checked before next task. Human reads results, not code.
6. **Test** — benchmark + trust test (see below).

Steps 2–5 are the Superpowers skill package for Claude Code (obra/superpowers).

## References in three roles (the "most transferable" idea)

Copying links and saying "build this" produces bad results — foreign solutions solve foreign problems. Each reference gets a role:

| Role | Question | In the video |
|------|----------|--------------|
| **Building block** (Baustein) | What do I adopt finished? | **qmd** (Tobi Lütke) — local hybrid search, installed as-is |
| **Pattern** (Muster) | Which idea do I adapt and implement myself? | **Karpathy's LLM wiki** — AI maintains markdown pages, small index read first, rules against contradictions and orphans |
| **Yardstick** (Messlatte) | What defines "good enough"? | AI-generated **mockup images** of the target UI, given to Claude as visual spec |

Also examined and *not* adopted (code-wise): **gbrain** (garrytan) and **graphify** — but their pattern "Markdown is the only truth; the graph is a derived intermediate" secured a core architecture decision. "Discarding is also a research result."

## Architecture: five building blocks

Color code on the board: orange = your data, green = deterministic code (same every run, free), purple = AI. **Minimize purple.** AI only where understanding is genuinely required.

1. **Workspace / vault** (orange). ~2000 notes, >4000 files, plus Claude projects, skills, memory, connectors. **Markdown is the only truth.** No database, no proprietary format. Everything else is a derived view that can be thrown away and rebuilt without losing knowledge. Contains folder `09_wiki`.
2. **Indexer** (green, no AI). "A librarian who registers books without reading them." Walks all folders; per file records: what (title, location, size), how connected (links, tags), which cluster. Writes two files:
   - a **map file** (nodes + edges, ready to render) → feeds the graph
   - **INDEX.md** — a catalog, one line per area and important file (not every note, or the catalog becomes a book). Claude reads this first on every question.
   Three rules (from gbrain/graphify): markdown is the only truth; the map is a derived intermediate regenerated every run, never hand-edited; extraction is strictly separated from display. Built from spec in four tasks, each with a test.
3. **qmd search** (green + small local models). Keyword search + meaning search. Three small local models (<3 GB total, downloaded on setup): one expands the query with related terms, one embeds notes/queries onto the "meaning map", one reranks the hits. Used in three places: terminal, by Claude as a ladder rung, in the web app search box. ~2 s CPU per search, no API tokens, works offline.
4. **Claude + rulebook** (purple — the only big purple box). The decisive thing is not the AI, it is `CLAUDE.md`. Core: the **Brain-First search ladder**:
   1. Read `INDEX.md` (a few hundred lines). If the source is listed, open exactly that.
   2. Check the wiki — is the knowledge already condensed there?
   3. Only then qmd search — check candidates *without* opening files.
   4. Open exactly **one** file — the best — and read only the relevant section.
   5. Then answer. No blind scanning of whole folders.
   Answers "how do I get the whole vault into the context window?" — you don't. Per question Claude loads the catalog plus a few relevant files, a few thousand tokens. "The trick is not a bigger context window; it is a system that does not need one." Claude also *writes* back: it maintains the wiki folder.
5. **Web app** (at the edge of the diagram, on purpose). Does exactly three things: reads the map file and draws the graph; opens any clicked note beside it; carries the search box wired to qmd. **It never writes, never decides, and nothing else needs it.** Blocks 1–4 are the system; the app is the window.

## The LLM wiki (capability 3, the heart)

- Folder `09_wiki`. Hard rule: the human never edits it. Every text in it is written by Claude.
- A **schema file** (plain text) inside the wiki folder is Claude's work instruction: page types (source summaries, topic pages, person/project pages, synthesis pages that condense multiple sources), cross-linking rules. Read before every wiki operation, so every Claude session follows identical rules.
- Main operation: **ingest**. Give Claude a new source (transcript, article, note). Claude reads it, uses the wiki's page index to find which pages the topic already touches, opens only those, updates them / creates missing ones / sets links — and on each page checks whether the new information **contradicts** what is already there.
- Contradictions are **marked, never overwritten**. Both statements stay, each with its source, plus "the human decides." Fix the *source*, not the warning — deleting the warning box just makes the next run find the same conflict. After deciding, tell Claude "decided, this holds"; the wiki updates, the box disappears, the decision goes into the log.
- Every ingest run is logged: when, which source, which pages changed. "The difference between a system you must believe and one you can verify."
- Live test: a note with three planted contradictions + one harmless statement → all three caught and marked (some on multiple pages); the harmless one was merged as confirmation of an open point. On the real vault: **52 conflict sites** found, including the strategy-target vs. actual-metrics example from the intro.
- Ingest never runs from the web app — deliberate. Claude is called from terminal, the Claude Code app, or inside Obsidian via a plugin (e.g. Claudian).
- Needs no special tech: normal markdown files, one folder, one rule file, Claude as librarian; any editor is the shelf.

## Benchmark (capability check)

Same five real work questions, once without the system, next morning with it (only qmd + rules installed in between). Measured tokens, time, correctness. Result: **~50 % fewer tokens, ~40 % less time, 5/5 correct in both runs.** One one-line question cost >500k tokens without the brain — cost comes from searching, since each search step re-reads the whole history. With the system, search ended after two steps. No gain on simple questions already in context; big gain on deeply buried knowledge and multi-file answers. Real test: still using it daily when the excitement is gone.

## The UI (built last; the expensive mistake)

Mistake: describing the desired look in words and iterating ("denser, 3D, more depth, less glow") — hours lost. Claude is excellent at reproducing concrete references and bad at guessing what's in your head.

Fix: generate the target state as **images** in ChatGPT first (clusters spatially separated, each with its own color; links appear only on hover; sphere size = amount of knowledge; detail panel opens at the side on click; a ring view with CLAUDE.md as core, knowledge/projects around it, external services outermost; a layers view). Give the images to Claude Code as the reference. Rule: Claude does one step → check in browser against the target image → sign off → next step. Views then took minutes. (Tip: Pinterest, "knowledge graph", "big data cloud" for visual references.)

Why an own app at all if Obsidian + Claude Code already do search/wiki/read? (1) Obsidian only sees notes; the system is bigger (Claude projects, skills, memory, connectors). (2) Health view — which clusters grow, what is orphaned. (3) Read and click on in the graph, including files outside the vault — the test of whether a visualization is a tool or a poster. If Obsidian is enough, skip the app. The app's search box also does meaning search (qmd fast variant: query expander + embedder, no reranker), fully local, zero API tokens. Tokens are spent in exactly one place in the whole system: when Claude actually thinks.

## Seven lessons

1. **References beat descriptions** — for tech and for looks.
2. **Small steps with sign-off**, never everything at once.
3. **Decide before building** — the spec is the contract. Build first, decide later = build twice.
4. **Deterministic where possible**; AI only where understanding is needed.
5. **Markdown stays the only truth** — no database, no format prison; everything else is a replaceable view.
6. **Every claim needs a checkpoint** — without the benchmark he would only *believe* it works.
7. **The human decides, the AI delivers.** Across the whole project the AI made zero decisions; it made them possible.

## Minimal entry (≈1 hour, no app, no graph, no wiki)

1. Order notes into topic clusters (with Claude Code's help).
2. Create an index file — one line per topic: what it is, where it is. First rung of the ladder.
3. Install and initialize qmd.
4. Put the Brain-First rules into `CLAUDE.md`.

Brain-First rules (from the video description, to copy):
```
Bei jeder Wissensfrage gilt diese Reihenfolge:
1. Lies zuerst INDEX.md (den Katalog) — steht die Quelle dort, öffne genau diese.
2. Prüfe dann das Wiki (verdichtetes Wissen), falls vorhanden.
3. Erst danach die Suche (qmd) — Kandidaten prüfen, ohne Dateien zu öffnen.
4. Öffne genau EINE Datei — die beste — und lies nur die relevante Sektion.
5. Dann erst antworten. Kein blindes Durchsuchen ganzer Ordner.
```

## Links from the video

- Superpowers: https://github.com/obra/superpowers
- qmd: https://github.com/tobi/qmd
- Karpathy LLM-wiki gist: https://gist.github.com/karpathy/442a… (truncated in description)
- gbrain: https://github.com/garrytan/gbrain
- graphify: https://github.com/Graphify-Labs/grap… (truncated)
- Obsidian: https://obsidian.md
- Start document: Skool community (free) — https://www.skool.com/the-node-ai
