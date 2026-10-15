# Benchmark YYYY-MM-DD

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
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |

Totals: A … tokens / B … tokens (… %). Verdict in one line.
