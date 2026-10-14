---
title: Transformer architecture
type: wiki-topic
created: 2026-10-15T00:55:25+02:00
updated: 2026-10-15T00:55:25+02:00
sources: [10_ai/1706.03762.md]
confidence: low
tags: []
---
# Transformer architecture

## Summary

The [Transformer](../entities/transformer.md) is an encoder-decoder model built from stacked self-attention and position-wise feed-forward layers, with no recurrence or convolution. Position information is injected through positional encodings added to the token embeddings.

## Claims

- Encoder and decoder are each a stack of N = 6 identical layers. ([1706.03762](../sources/1706.03762.md))
- An encoder layer has a [multi-head](multi-head-attention.md) self-attention sub-layer and a position-wise feed-forward sub-layer; the decoder adds a third sub-layer attending over the encoder output. ([1706.03762](../sources/1706.03762.md))
- Every sub-layer output is LayerNorm(x + Sublayer(x)); all sub-layers and embeddings use d_model = 512. ([1706.03762](../sources/1706.03762.md))
- Decoder self-attention is masked so position i can depend only on outputs before i, preserving auto-regression. ([1706.03762](../sources/1706.03762.md))
- The feed-forward network is two linear transformations with a ReLU in between, inner dimension d_ff = 2048. ([1706.03762](../sources/1706.03762.md))
- Sinusoidal positional encodings were chosen over learned ones (nearly identical results) because they may extrapolate to longer sequences. ([1706.03762](../sources/1706.03762.md))
- Removing recurrence allows much more parallelisation: the base model trained in 12 hours on eight P100 GPUs. ([1706.03762](../sources/1706.03762.md))

## Open questions

- Restricting self-attention to a neighbourhood of size r for very long sequences was proposed as future work. ([1706.03762](../sources/1706.03762.md))

## Related

- [Attention mechanism](attention-mechanism.md)
- [Multi-head attention](multi-head-attention.md)
- [Transformer](../entities/transformer.md)
