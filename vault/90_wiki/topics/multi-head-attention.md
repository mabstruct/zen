---
title: Multi-head attention
type: wiki-topic
created: 2026-10-15T00:55:25+02:00
updated: 2026-10-15T00:55:25+02:00
sources: [10_ai/1706.03762.md]
confidence: low
tags: []
---
# Multi-head attention

## Summary

Multi-head attention runs several [attention](attention-mechanism.md) functions ("heads") in parallel. Queries, keys and values are linearly projected h times with different learned projections; each head applies scaled dot-product attention; the head outputs are concatenated and projected once more. This lets the model attend jointly to information from different representation subspaces at different positions, which a single head would average away.

## Claims

- MultiHead(Q, K, V) = Concat(head₁, …, head_h) Wᴼ, where headᵢ = Attention(QWᵢQ, KWᵢK, VWᵢV). ([1706.03762](../sources/1706.03762.md))
- The original Transformer uses h = 8 heads with d_k = d_v = d_model / h = 64, so total cost is similar to single-head attention at full dimensionality. ([1706.03762](../sources/1706.03762.md))
- Multi-head attention counteracts the reduced effective resolution caused by averaging attention-weighted positions. ([1706.03762](../sources/1706.03762.md))
- The Transformer uses it in three ways: encoder self-attention, masked decoder self-attention, and encoder-decoder attention (queries from the decoder, keys and values from the encoder output). ([1706.03762](../sources/1706.03762.md))
- Single-head attention is 0.9 BLEU worse than the best setting; quality also drops off with too many heads. ([1706.03762](../sources/1706.03762.md))
- Individual heads appear to learn different tasks, many related to the syntactic and semantic structure of sentences. ([1706.03762](../sources/1706.03762.md))

## Open questions

- What number of heads is best beyond the 1–32 range tested on one translation task?

## Related

- [Attention mechanism](attention-mechanism.md)
- [Transformer architecture](transformer-architecture.md)
- [Transformer](../entities/transformer.md)
