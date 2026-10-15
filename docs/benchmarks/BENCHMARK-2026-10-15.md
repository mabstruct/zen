# Benchmark 2026-10-15

Five real questions, each asked twice.

## Method

- One fresh Claude Code session per question and per arm. Never share a session between arms.
- A: plain session in `zen/` with the instruction "answer from the files in vault/; do not use skills".
- B: `/zen-ask <question>`.
- Tokens: the session total from `/cost`, taken right after the answer.
- Time: stopwatch from pressing Enter to the final answer.
- Correct: judged against the source file you know holds the answer.
- Cited: whether the answer names the right vault path.

| # | question | A tokens | A time | A correct | A cited | B tokens | B time | B correct | B cited |
|---|----------|----------|--------|-----------|---------|----------|--------|-----------|---------|
| 1 | when did Russel present “Relations Between the Spectra and Other Characteristics of the Stars” to the Royal Astronomic Society| 267k | 14s | x | x  | 460k | 40s | x | x |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |

Totals: A … tokens / B … tokens (… %). Verdict in one line.


## Analysis

I stopped here, beacsue it became clear we have the following problem:

Claude’s instructions dominate. The system prompt, tool list, project rules, and skill text come to roughly 88 thousand tokens, and they are sent with every one of the five model calls. The first call had to write them into the cache, which is the expensive part. The later four calls only re-read them.
Reading the vault was cheap. The index check, the two index files, and the Russell wiki page together added about 14 thousand effective tokens.
The answer itself was tiny. All of Claude’s writing across the five calls, including the task-list updates, came to about 1,300 output tokens, which weighs in at under 7 thousand effective.
Your question barely registers. The prompt text was a few dozen tokens.

The practical takeaway is that each extra model call in this session costs about 9 thousand effective tokens just to re-read the standing instructions, before any real work happens. Fewer round trips per question is the main lever.
## Q1, arm B re-run after `zen-ask-prep` (v1.1)

- Model calls: 3 (prep, one file, answer) — down from 5–6.
- Instructions still dominate: ~27k tokens written to cache once (2x), then ~243k cached re-reads across the 3 calls (0.1x). This is session overhead (system prompt, tool list, CLAUDE.md, hook text, skill prompt), not vault work.
- Vault work: prep output (both indexes + hits) ~5.5k tokens, the Russell wiki page ~1.4k — about one seventh of the cost.
- Claude's own writing: 717 tokens across three replies and two commands.
- Warm-session estimate for the same question: ~35k effective tokens (the 27k cache write does not recur).

Conclusion: `zen-ask-prep` removes the round-trip penalty; the remaining lever is a slim session profile for ZEN work (fewer plugins, MCP servers and hooks), which is outside the tools.
