# Planned ingest, run 1 (2026-10-15)

Does splitting ingest into one planner and parallel page writers cut wall time?

**Short answer:** no, not with this plan format. The run took about 15 minutes against 14 for the single-agent ingest. The mechanics worked, but the slow part moved into the planner instead of being spread across writers.

## Setup

- **Input:** `10_ai/2025-05-12-o3-categories-of-llm-training-v02.md`, 79 KB of extracted text (an o3-written overview of LLM training).
- **Baseline:** the first ingest of the same document on the single-agent path with the deep ingester. It took about 14 minutes and wrote 34 pages (29 new, 5 updated), about 10,600 words.
- **This run:** workspace branch `measure-parallel`, rolled back to the state before that ingest (29 pages removed, 5 restored, LOG entry and companion stamp removed). `/zen-ingest` in a fresh session on `zen` branch `parallel-ingest`. Routing chose the deep model and the planned path, because 79 KB is above both the 50 KB and the 20 KB thresholds.
- **Plan format:** every claim written in final form, with its citation, inside the plan. Writers only transcribed.

## Result

| phase | time |
|---|---|
| planner (deep model) | ~11 min |
| 5 page writers, in parallel | ~46 s |
| `zen-plan finish`, re-index, qmd refresh | ~1 min |
| **whole run** | **~15 min** |

| | single-agent (baseline) | planned (this run) |
|---|---|---|
| wall time | ~14 min | ~15 min |
| pages created | 29 | 22 (source + 12 topics + 9 entities) |
| pages updated | 5 | 4 (the Transformer pages) |
| conflicts | none | none |
| Health afterwards | clean | clean, no broken links |

The plan passed `zen-plan check`, the writers stayed within their batches, and `finish` wrote the source page, companion stamp, LOG entry and wiki INDEX correctly. The companion summary flagged the document as o3's unverified account and noted the corrected STaR citation.

## Why there was no gain

Asking the planner for "claims in final form" meant the planner wrote the content of every page. About 10k words of premium-model generation stayed sequential in one agent. The writers only copied that text into files, which is why five of them together needed 46 seconds. Parallelism only helps if the generation happens in the parallel part.

The lower page count (22 vs 34) came from the planner's own choices, not from a rule. It may vary between runs.

## Next

**Thin plan:** the planner decides only the structure. That means pages and paths, a one-line brief per page, the source line ranges relevant to each page, the links, and the conflicts with their ids. Writers read their line ranges and write the claims themselves, in parallel. Expected: a few minutes of planning plus the slowest writer. This will be measured on the same document and branch as run 2.
