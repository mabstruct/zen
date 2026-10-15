# Planned ingest, runs 1 and 2 (2026-10-15)

Does splitting ingest into one planner and parallel page writers cut wall time?

**Short answer:** yes, once the plan is thin. Run 1 had the planner write every claim and took about 15 minutes against 14 for the single-agent ingest; the slow part only moved into the planner. Run 2 had the planner decide structure only and let the writers write the claims: about 9¼ minutes, with the same number of pages and slightly more text.

## Setup

- **Input:** `10_ai/2025-05-12-o3-categories-of-llm-training-v02.md`, 79 KB of extracted text (an o3-written overview of LLM training).
- **Baseline:** the first ingest of the same document on the single-agent path with the deep ingester. It took about 14 minutes and wrote 34 pages (29 new, 5 updated), about 10,600 words.
- **Run 1:** workspace branch `measure-parallel`, rolled back to the state before that ingest (29 pages removed, 5 restored, LOG entry and companion stamp removed). `/zen-ingest` in a fresh session on `zen` branch `parallel-ingest`. Routing chose the deep model and the planned path, because 79 KB is above both the 50 KB and the 20 KB thresholds.
- **Run 1 plan format:** every claim written in final form, with its citation, inside the plan. Writers only transcribed.

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

## Run 2: thin plan

**Thin plan:** the planner decides only the structure. That means pages and paths, a one-line brief per page, the source line ranges relevant to each page, the links, and the conflicts with their ids. Writers read their line ranges and write the claims themselves, in parallel. Expected: a few minutes of planning plus the slowest writer. Measured on the same document and branch, rolled back again to the same state (run 1's output kept in `git stash`). The planner still ran on the deep model, so only the plan format changed.

| | single-agent (baseline) | planned, run 1 (fat plan) | planned, run 2 (thin plan) |
|---|---|---|---|
| wall time | ~14 min | ~15 min | **~9 min 15 s** |
| pages created (incl. source) | 29 | 22 | 29 (source + 18 topics + 10 entities) |
| pages updated | 5 | 4 | 4 |
| words on new pages | ~10,600 | — | ~11,400 |
| conflicts | none | none | **1 (#c-0004)** |
| Health afterwards | clean | clean | clean, index current |

Phase timings were not broken out for run 2.

**A real conflict for the first time.** `#c-0004` on `topics/attention-mechanism.md`: the 2017 paper gives a recurrent layer a path length that grows linearly, O(n). The o3 overview instead blames a "quadratic path length" on RNN/CNN pipelines. The paper's statement is the established one, but the decision is the human's (`/zen-ingest --resolve`). Neither earlier run raised this.

**The writers also flagged tensions inside the o3 document itself.** These are not wiki conflicts, because a source cannot conflict with itself. GRPO is called "gradient-free" while its policy-gradient formula is given; the page records both under Open questions. The 70B size of R1-Zero and the ~100x LoRA memory figure are marked as unverified o3 claims. Writers reading the source lines directly is what made these visible.

## What the runs show

- The parallel step only saves time when the generation happens in it. Run 1's writers needed 46 seconds for five batches, because the planner had already written everything.
- With a thin plan, the planner (deep model, reading the whole document) is the remaining sequential part. The next lever is running the planner on the standard model, since deciding structure needs less depth than writing claims. That is not measured yet.
- Writers that read the source themselves produced more scrutiny (in-document tensions, unverified figures), not less.
- One document, one run per format: treat these as strong hints, not measurements.
