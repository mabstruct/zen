# zen-ui — a browsable knowledge graph for ZEN

Status: draft, 2026-10-19. A competing next step to zen-ask v2 (`2026-10-18-zen-ask-v2-design.md`); §8 compares the two. Adds `ui/` (a Node + Vite app), two fields to `_meta/map.json`, and a publish script. Changes nothing in the vault, the wiki SCHEMA, ingest or ask.

## 1. Intent

The user gathers sources for projects and work so they can find what they gathered and connect it into insights. The terminal and `/zen-ask` answer single questions, but nothing shows the whole: there is no overview of the knowledge and no way to browse along its connections.

The model is the user's earlier CONSTRUCT site (`https://mabstruct.ai/#/knowledge-graph`, source in `mabstruct/mabstruct-site/website/mabstruct-presence`). It has a force-directed graph of cards, coloured by card type and sized by confidence. Hovering a node highlights its connections, and clicking a node opens the card in a side panel. zen-ui does the same for ZEN, with one difference the user named: a node is a wiki page, and once you are reading wiki content you keep browsing by clicking its links, not only the dots.

zen-ui is also the user's main UX target. It ends as a Docker-deployed, interactive knowledge base the user can demo to the outside world. The user stays the knowledge admin: ingestion happens locally through the existing skills, and the GUI shows the result.

The user's decisions, from the brainstorm on 2026-10-19:

- **Graph first.** The home screen is the graph. Clicking a node opens the page in a reader panel.
- **Links are live in the reader.** Clicking a link inside a wiki page opens that page and moves the graph to it.
- **Node types:** wiki pages and sources, with the kind of wiki page visible (topic, entity, synthesis). Wiki pages cite sources, and that citation is an edge.
- **Size = confidence, plus hubs.** The wiki's `confidence:` field sets a wiki page's size step, and a page grows slightly with the number of pages linking to it, so hubs stand out while most pages are still `low`. Sources have a fixed size and their own shape. (Chosen after the review showed 125 of 131 wiki pages are `low`.)
- **Read-only** in the first version.
- **Roadmap:** v1 browse → v2 an ask field with results in the GUI → v3 the LLM behind ask is chosen by configuration. Deployment is Docker on web hosting.
- **No public/private filtering.** One ZEN install is one audience: the user runs a private ZEN and, separately, a public one. zen-ui shows the whole vault it is built from.

## 2. Goals, non-goals, anti-goals

Goals (v1)

1. Open the app and see every wiki page and every source as one graph, coloured by kind and sized by confidence.
2. Click any node and read the page, rendered, in a side panel.
3. Click any link in that page to go to the target page. The graph re-centres on it and the trail records the step.
4. A source can be read both as its wiki summary and as its companion or note text.
5. Every page has its own URL, so a link to a page can be shared and reopened.
6. `scripts/ui-publish.sh` builds a Docker image that serves the app with a snapshot of the vault, and the image runs on any host that runs containers.

Non-goals (v1)

- No ask, no search beyond finding a page by title, and no model calls. Ask is v2.
- No editing, annotation or ingest from the GUI.
- No public/private filtering, no login and no per-cluster export.
- No entity subtypes (person, project, tool, organisation). The pages do not record them yet (§9).
- No `_originals/` in the app or the image, so no PDF viewer.

Anti-goals: the work fails even if it runs when:

- The app or its build writes to `vault/`.
- A link inside a wiki page goes nowhere or leaves the app, when its target is a page the graph contains.
- A source shows up as two unrelated dots (its wiki summary and its vault file).
- The deployed image contains anything that isn't the built app and the vault snapshot: no `_originals/`, no repo, no `.env`.
- The graph is unreadable at today's size (about 150 nodes, 1,650 edges) on a laptop screen.

## 3. Roadmap

| version | user gets | needs underneath |
|---------|-----------|------------------|
| **v1 browse** (this spec) | graph, reader, live links, trail, shareable URLs, Docker image | vault snapshot and `map.json` only; static files served by a web server |
| **v2 ask** | an ask field and its answer in the GUI: ranked entries, each opening in the reader | a small server that runs retrieval and one model call, reusing zen-ask v2's `zen-ask-prep` / `zen-ask-open` logic; an API key on the server; a rate limit or access code against budget burn |
| **v3 models** | choose the model behind ask by configuration | a provider setting in the server config, keys from the environment |

v1 must not block v2. The v1 image serves static files, and v2 adds a server process to the same image. Keep the app's data access behind one module (`ui/src/data.ts`) so v2 can switch it from static files to an API without touching the views.

## 4. Constraints

- **Stack (my call, following the CONSTRUCT site):** React 19, Vite 7, Tailwind 4, lucide-react, and TypeScript. Layout uses `d3-force`, the only graph library; drawing is SVG while the graph stays under about 500 nodes. Markdown rendering uses `marked`, as the site's tooling does.
- Node 26 is installed locally, as is Docker.
- `vault/` is a separate private git repo and is in `.gitignore`. The app's source is checked in under `ui/`. The vault snapshot is a build output and is never committed.
- `_meta/map.json` is derived by `zen-index` (Python, `tools/src/zen/map_json.py`) and may be stale. The publish script runs `(cd tools && uv run zen-index --vault ../vault)` first.
- Today's `map.json`:
  - Node types include `wiki-topic`, `wiki-entity`, `wiki-source`, `wiki-meta`, `companion`, `note`, `original` and `tag`.
  - Edge kinds are `link` (a markdown link between vault files), `wiki` (a wiki page's `sources:` entry to its vault file), `source` (a companion to its original) and `tag`.
  - Nodes carry no `confidence` and no conflict ids.
- Wiki pages have frontmatter `confidence: low | medium | high`, where low means 1 source, medium means 2–3 agreeing and high means 4 or more agreeing. Source pages are always `high`. Conflict blocks look like `> [!conflict] #c-NNNN — open`, and the scanner already reads them (`Doc.open_conflicts`).
- Companions can be large (Gilgamesh is 487 KB). Load a page's text only when it is opened, never the whole vault up front.

## 5. The parts

### 5.1 `map.json` gains two fields (Python, `zen-index`)

Add `confidence` (string or null) and `conflicts` (the list of open conflict ids, empty if none) to every node in `map_json.build`. The change is additive, so existing readers (zen-ask prep, health) are unaffected. Tests go in the existing `tools/tests` style. This is the only change outside `ui/` and `scripts/`.

### 5.2 Snapshot builder: `ui/scripts/snapshot.ts`

This is a Node script run by `scripts/ui-publish.sh` and by `npm run dev`, never inside Docker (the `ui/`-only build context cannot reach the vault). It reads `--vault <path>`, defaulting to `../vault`, and writes `ui/public/data/`, which is gitignored:

- **`graph.json`**: nodes and edges for the graph, derived from `map.json`.
  - Nodes include every `wiki-topic`, `wiki-entity` and `wiki-synthesis`, plus one **source node** per vault file of type `companion` or `note`. A source node merges the vault file and its `wiki-source` page when one exists (found through the `wiki` edge from the source page). Its id is the vault path.
  - Excluded: `wiki-meta` (INDEX, LOG, SCHEMA), `original`, `tag`, the vault `INDEX.md`, `00_inbox/`, `01_daily/` and `02_templates/`.
  - A source with no wiki-source page is still a node, drawn dimmed and labelled "not ingested" (my call).
  - Each node carries `id`, `title`, `kind` (topic | entity | synthesis | source), `cluster` (the vault cluster for a source; for a wiki page, the clusters of its `sources:`), `confidence`, `conflicts`, `updated`, and the paths of its readable texts (`wiki` and/or `vault`).
  - Edge kinds:
    - `cites`: a wiki page to a source node. Derived from links to `90_wiki/sources/*` pages, mapped to the merged source node, plus the `wiki` edges.
    - `links`: wiki page to wiki page, from `link` edges, excluding links that come from INDEX/LOG.
    - `conflict` (my call): **source A ↔ source B** of each **open** conflict block, taken from the two `sources/` links on the block's `A:` and `B:` lines and mapped to the merged source nodes. A conflict is a disagreement between two sources, and today's only open conflict (`#c-0004`, on `topics/attention-mechanism.md`) sits on a single page, so page-to-page edges would draw nothing. The edge carries the conflict id and the page(s) holding the block; clicking it opens the first such page. Resolved conflicts draw no edge; they are only styled in the reader (muted callout).

    Edges are deduplicated and undirected for drawing; the direction is kept in the data.
- **`pages/<vault path>`**: a copy of each readable markdown file the graph refers to: wiki pages and the companions and notes behind source nodes. Never `_originals/`.

Tests (vitest) run against a small fixture vault in `ui/test/fixture-vault/`. They cover the merge of a source page and its vault file, the exclusions, the three edge kinds, the dimmed un-ingested source, and that nothing under `_originals/` is copied.

### 5.3 The app (`ui/src/`)

Layout: the graph fills the left, the reader panel sits on the right, and the reader can be collapsed. Phone width is out of scope for v1 (my call); a laptop is the demo screen. The dark visual style follows the CONSTRUCT site.

**Graph view**
- `d3-force` layout. Colour shows kind: topic, entity, synthesis and source each get one colour, with a legend whose entries toggle that kind on and off, as in CONSTRUCT.
- Size, for wiki pages: a base radius per confidence step (low < medium < high), plus a small increase with in-degree (incoming `links` and `cites`, capped so confidence remains the bigger step). Sources: one fixed radius and a distinct shape, since a source page's `high` means only that it summarises faithfully. The `graph.json` node carries `inDegree` for this.
- `cites` and `links` edges are thin and neutral. A `conflict` edge is red and dashed.
- Hovering a node highlights it, its neighbours and the edges between them, and dims the rest. The tooltip shows the title, kind, confidence and the number of sources.
- Clicking a node opens it in the reader and centres it.
- Controls: Reset, Labels on/off, colour by kind ↔ by cluster, and a find-by-title box that jumps to the matching node.
- Drag and zoom are supported.

**Reader panel**
- A header with the title, kind, confidence (dots, as in CONSTRUCT), clusters, updated date, and any open conflict ids.
- The body is the page's markdown rendered without frontmatter. Conflict blocks are styled as callouts: open ones red, resolved ones muted.
- **Links:** every relative markdown link whose target is a node, or a page belonging to a node, becomes in-app navigation. It opens the target, centres the graph on it and appends to the trail. A link to `_originals/` renders as plain text marked "original not published". An external `http(s)` link opens in a new tab. Any other relative link renders as plain text.
- A source node has two tabs: **Wiki summary** (the wiki-source page) and **Text** (the companion or note). The Text tab is the default when no wiki-source page exists. For a companion, the Text tab shows `## Summary` first, with `## Extracted text` collapsed until expanded.
- **Trail:** the pages visited in this session, as clickable breadcrumbs. It is cleared by Reset.

**Routing:** hash routes, `#/` for the graph alone and `#/p/<vault path>` for a page open. A shared URL opens the page with the graph centred on it.

**Data access:** all fetches go through `ui/src/data.ts` (`getGraph()`, `getPage(path)`), which reads the static files in v1.

### 5.4 Docker and publish

`ui/Dockerfile` is a multi-stage build: a Node stage runs `npm ci && npx vite build` on the already-generated `public/data/`, and an `nginx:alpine` stage serves `dist/` with a single-page-app fallback. The image takes no runtime configuration in v1.

`scripts/ui-publish.sh [--tag <tag>]` runs from `zen/`. It runs `zen-index`, runs the snapshot, then `docker build -t zen-ui:<tag> ui/`. The build context is `ui/` only, so the vault, the repo and `.env` cannot enter the image. Its `.dockerignore` excludes `node_modules` and the test fixtures. The script prints the image size and the node and edge counts.

Pushing to a registry and running the container on a host are left to the builder and the user's host (§7). The README gets a short "publish" section.

`.superpowers/` (brainstorm mockups) is added to `.gitignore`.

## 6. Testing and success

- Unit: the snapshot tests (§5.2) and the `map.json` field tests (§5.1).
- Component (vitest + Testing Library):
  - the link rewriter maps a relative wiki link to in-app navigation, an `_originals/` link to text, and an external link to a new tab;
  - the reader's source tabs.
- Smoke (Playwright, one test, against `vite preview` on the fixture vault): open `#/`, click a node, click a link in the reader, and assert that the URL, the reader title and the trail changed.
- Done means `scripts/ui-publish.sh` produces an image, and `docker run -p 8080:80 zen-ui` serves the real vault. The user can then:
  1. open `Babylonian Netherworld` from the graph;
  2. follow a claim's citation to `The Epic of Gilgamesh`;
  3. switch to its Text tab;
  4. go back through the trail;
  5. share the URL of a page and reopen it.

## 7. Left to the builder

- Colours, radii, force parameters and label collision.
- Component structure and state management (plain React state is enough).
- Whether `snapshot.ts` reads `map.json` alone or also parses frontmatter. `map.json` must remain the source of node and edge membership.
- The nginx config details, and the image tag scheme.
- Registry and hosting. The user has not named a host; the image must run anywhere `docker run` works.

## 8. zen-ask v2 or zen-ui first: the decision

| | zen-ask v2 first | zen-ui v1 first |
|---|---|---|
| what improves | answers in the terminal: ranked readings, chunk-level, connections | overview and browsing: see the whole, follow connections, demo it |
| who sees it | the user, in Claude Code | the user and outside visitors |
| depends on the other | no | no |
| feeds the other | yes, its `zen-ask-prep`/`zen-ask-open` become zen-ui v2's backend | yes, its reader becomes where v2 shows ask's entries |
| size | 8 planned tasks, Python, plan written | about 6–8 tasks, mostly TypeScript; plan not yet written |
| risk | retrieval quality; measurable by its fixture | graph readability at 150+ nodes; checkable by eye on the real vault |

Branching (my call): zen-ui starts from `main`, not from `ask-v2`. The two touch no common code; the ask-v2 plan leaves `map_json.py` alone.

The two are a sequence, not rivals: zen-ui v2 needs zen-ask v2's tools. Either order works. Building zen-ui v1 first gets the main UX target and the demo sooner, and zen-ask v2 then lands as the engine for zen-ui v2. Building zen-ask v2 first gives v2 of the GUI a tested backend to call.

## 9. Follow-ups (not in v1)

- **Entity subtypes:** add `kind: person | project | tool | organisation` to the SCHEMA's entity frontmatter so `/zen-ingest` writes it, and backfill the 64 existing entity pages through a re-ingest or a deliberate `fix` run. The graph then colours entities by kind. This is a wiki rule change, so it goes through the SCHEMA and ingest, never through the GUI.
- **Typed links** (supports, extends, contradicts), as in CONSTRUCT. ZEN links are untyped today; only `cites`, `links` and `conflict` can be told apart.
- **v2 ask and v3 models**, each with its own spec.
