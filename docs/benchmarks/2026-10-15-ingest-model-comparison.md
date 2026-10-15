# Ingest model comparison 2026-10-15

Does wiki ingestion need a premium model, or is a mid-tier model good enough?

**Short answer:** Sonnet 5.5 is good enough for a routine first ingest. It was as accurate as Fable 5.1, cost less, and took less than half the time. Fable 5.1 wrote a richer wiki: more numbers, more mechanisms, more cross-links. Use the premium model where depth or judgement pays off.

## Method

- **Input:** one companion, `15_cosmology/sample-seventh.md`. It is Chapter 7, "Seventh rung: the Milky Way", 128 KB of extracted PDF text, about 1,900 lines.
- **Fable 5.1 arm:** the real ingest, run by `/zen-ingest` in the live vault.
- **Sonnet 5.5 arm:** a scratch copy of the vault, rolled back to the exact state before the Fable ingest. The wiki index, log and companion were restored, and the extracted text was confirmed byte-identical. The brief was word-for-word the same, with only the vault path changed.
- **Isolation check:** the Sonnet transcript shows it read only the scratch vault. It never touched the live vault, so its output is independent.
- **Structural checks:** a script checked both outputs for citations on every claim, broken links, required frontmatter, index sort order and summary length.
- **Quality review:** a separate Opus 5.5 reviewer got both page sets labelled only A and B. It read the whole chapter and checked every claim on all 24 pages of each side against the source text. A was Sonnet and B was Fable. The reviewer was not told which was which.
- **Spot check:** the reviewer's main error findings were confirmed against the chapter text by hand.

Caveat: this is one document and one run per model. Model output varies from run to run, so treat the result as a strong hint, not a measurement.

## Cost and speed

| | Fable 5.1 | Sonnet 5.5 |
|---|---|---|
| Wall time | 5 min 58 s | 2 min 36 s |
| Subagent tokens | 159,446 | 137,938 |
| Tool calls | 14 | 13 |

Sonnet is also much cheaper per token, so the price gap is larger than the token gap.

## Structure

Both outputs pass every structural check. Both chose the same 24 pages on their own: 1 source page, 8 topics and 15 entities with identical names. Both skipped Kapteyn, Shapley and Leavitt as passing mentions.

| | Fable 5.1 | Sonnet 5.5 |
|---|---|---|
| Body words, all pages | 6,112 | 4,335 |
| Claim bullets on topic and entity pages | 133 | 113 |
| Bullets without a citation | 5 | 0 |
| Broken links | 0 | 0 |
| Missing frontmatter fields | 0 | 0 |
| Index sorted | yes | yes |
| Companion summary | 3 lines, 140 words | 4 lines, 93 words |

The five uncited Fable bullets are all "None recorded." placeholders under Open questions, not real claims.

## Accuracy

| | Fable 5.1 | Sonnet 5.5 |
|---|---|---|
| Claims checked | about 158 | about 134 |
| Factual errors | 4 (1 clear, 3 minor) | 2 (both minor) |
| Unsupported claims | 7 (all minor) | 3 (all minor) |

Two of the unsupported claims appear on both sides: "Saha's ionisation equation" and the Hugginses "in England". Neither is in the chapter, though both are true.

**Fable 5.1 errors:**
- **Clear:** the Pickering entity page gives "(1846–1919)" as his years as Harvard director. Those are his birth and death years, taken from a figure caption.
- It dates Russell's first chart to 1913. The talk was in 1913 and the chart was published the following year.
- It credits Hertzsprung with the 1910 Pleiades diagram, which a Potsdam colleague drew. Fable's own H-R topic page has this right.
- It calls Fleming "likely" the maid in the anecdote. The chapter says so definitely.

**Sonnet 5.5 errors:**
- It says Pickering found Maury's system unwieldy. The chapter gives that judgement to "the astronomers and computers". Pickering only doubted the level of detail.
- It lists Leavitt among the spectral classifiers. The chapter ties her only to variable stars.

Fable's extra unsupported claims are small embellishments, such as calling Thomas Wright the "first" to propose the disc model.

## Coverage

Sonnet left out material the chapter treats as important:
- What happens to stars after the main sequence: white dwarfs, supergiants, supernovae, neutron stars and black holes.
- How the Russell–Vogt theorem works, beyond its headline.
- The standard candle idea, the Pleiades and Hyades as calibrators, and dust reddening as the limit on range.
- The worked numbers, such as flux at Mars and Pluto, Sirius at −1.46, and JWST reaching magnitude 34.
- Background on Cecilia Payne, and her result that all other elements make up less than 2%.

Fable left out less:
- The chapter's closing pointer to Leavitt's Cepheids as the next rung. Sonnet has this in its summary and source page.
- The opening survey of world myths about the Milky Way, which is minor.

## Usefulness for later questions

- **Sonnet 5.5** answers "what happened" well. It is weaker on "how much", "when exactly" and "how does it work". Several topic pages are thin, and its entity pages rarely link to each other.
- **Fable 5.1** includes formulas, concrete values, paper titles and dates for nearly every step. Its pages link to each other densely, and it covers the chapter's maths section far better.

The reviewer's verdict: Fable is slightly better overall, with moderate confidence. Its lead is in coverage and retrieval value, while Sonnet is slightly ahead on accuracy.

## Recommendation

- **Use Sonnet 5.5 for routine first ingests,** especially notes, articles and short documents. Its accuracy matched the premium model, and its gaps are omissions, not distortions. Omissions are the safer kind of failure, because the companion keeps the full text.
- **Use the premium model where depth or judgement pays off:**
  - Long, technical or numeric documents like this chapter, if you want to answer detailed questions from the wiki alone.
  - Re-ingests, and documents in topics the wiki already covers, because conflict detection gets harder as the wiki grows. This test could not measure that, since the chapter touched no existing pages.
  - Synthesis pages.
- **Whichever model runs it,** check dates in parentheses next to names. Both models made their worst slips on dates and attributions.

To route by model, the ingest skill can pass a model when it dispatches the subagent. An agent definition can also name one in its frontmatter.

## Follow-up on the live wiki

The live wiki still holds the Fable errors listed above. The clearest is the Pickering date range on [edward-pickering.md](../../vault/90_wiki/entities/edward-pickering.md). The wiki changes only through `/zen-ingest`, so they stay until a re-ingest or a logged fix corrects them.
