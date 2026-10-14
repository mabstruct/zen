---
title: Attention mechanism
type: wiki-topic
created: 2026-10-15T00:55:25+02:00
updated: 2026-10-15T00:55:25+02:00
sources: [10_ai/1706.03762.md]
confidence: low
tags: []
---
# Attention mechanism

## Summary

An attention function maps a query and a set of key-value pairs to an output: a weighted sum of the values, where each weight comes from a compatibility function of the query with the corresponding key. The [Transformer](../entities/transformer.md) builds an entire sequence model from attention alone.

## Claims

- Attention lets a model relate positions regardless of their distance in the input or output sequence. ([1706.03762](../sources/1706.03762.md))
- Scaled dot-product attention computes softmax(QKᵀ / √d_k) V over packed matrices of queries, keys and values. ([1706.03762](../sources/1706.03762.md))
- Without the 1/√d_k scaling, large d_k makes dot products grow large and pushes softmax into regions with extremely small gradients; additive attention then outperforms unscaled dot-product attention. ([1706.03762](../sources/1706.03762.md))
- Dot-product attention is much faster and more space-efficient than additive attention in practice because it uses optimised matrix multiplication. ([1706.03762](../sources/1706.03762.md))
- Self-attention relates different positions of a single sequence to compute a representation of that sequence. ([1706.03762](../sources/1706.03762.md))
- A self-attention layer connects all positions with a constant number of sequential operations, versus O(n) for a recurrent layer. ([1706.03762](../sources/1706.03762.md))

## Open questions

- Reducing d_k hurts quality, suggesting a more sophisticated compatibility function than the dot product may help. ([1706.03762](../sources/1706.03762.md))

## Related

- [Multi-head attention](multi-head-attention.md)
- [Transformer architecture](transformer-architecture.md)
- [Transformer](../entities/transformer.md)
