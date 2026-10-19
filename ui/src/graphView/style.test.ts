import { expect, test } from 'vitest'
import type { GNode, Graph } from '../types'
import { findByTitle, neighbourhood, nodeColour, nodeRadius, visible } from './style'

const n = (o: Partial<GNode>): GNode => ({
  id: 'x', title: 'X', kind: 'topic', clusters: ['10_a'], confidence: null, conflicts: [],
  updated: null, wiki: null, vault: null, ingested: true, inDegree: 0, ...o,
})
const NODES = [n({ id: 'a', title: 'Jürgen Schmidhuber' }), n({ id: 'b', title: 'Attention mechanism' }), n({ id: 'c', title: 'Self-attention in depth' })]
const G: Graph = {
  generated: '2026-10-19T00:00:00+00:00',
  nodes: [n({ id: 'topic' }), n({ id: 'ent', kind: 'entity' }), n({ id: 'src', kind: 'source' }), n({ id: 'far', kind: 'synthesis' })],
  edges: [
    { from: 'topic', to: 'src', kind: 'cites' },
    { from: 'topic', to: 'ent', kind: 'links' },
    { from: 'far', to: 'src', kind: 'conflict', conflict: 'c-0001', pages: ['far', 'src'] },
  ],
}

test('confidence step dominates the hub bonus; sources fixed', () => {
  expect(nodeRadius(n({ confidence: 'medium', inDegree: 0 }))).toBeGreaterThan(nodeRadius(n({ confidence: 'low', inDegree: 10_000 })))
  expect(nodeRadius(n({ confidence: 'low', inDegree: 8 }))).toBeGreaterThan(nodeRadius(n({ confidence: 'low', inDegree: 0 })))
  expect(nodeRadius(n({ kind: 'source', confidence: null, inDegree: 50 }))).toBe(7)
})
test('findByTitle folds case and diacritics', () => {
  expect(findByTitle(NODES, 'jurgen')?.title).toBe('Jürgen Schmidhuber')
  expect(findByTitle(NODES, 'ATTENTION')?.title).toBe('Attention mechanism')
  expect(findByTitle(NODES, 'zzz')).toBeNull()
})
test('neighbourhood and visible', () => {
  expect(neighbourhood(G, 'topic')).toEqual(new Set(['topic', 'src', 'ent']))
  expect(visible(G, new Set(['entity'])).edges.some(e => e.to === 'ent')).toBe(false)
})
test('nodeColour: kind colours differ, cluster is stable', () => {
  expect(nodeColour(n({ kind: 'topic' }), 'kind')).not.toBe(nodeColour(n({ kind: 'entity' }), 'kind'))
  expect(nodeColour(n({ clusters: ['12_x'] }), 'cluster')).toBe(nodeColour(n({ clusters: ['12_x'], kind: 'source' }), 'cluster'))
})
