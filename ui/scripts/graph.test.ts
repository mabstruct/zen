import { describe, expect, test } from 'vitest'
import { buildGraph, parseConflicts } from './graph.ts'
import { owners, resolvePath } from '../src/graph.ts'
import type { MapNode, ZenMap } from '../src/types.ts'

const mk = (id: string, type: string, cluster: string | null, extra: Partial<MapNode> = {}): MapNode => ({
  id, path: type === 'tag' ? null : id, title: id, type, cluster, updated: '2026-10-01T00:00:00+02:00',
  confidence: null, conflicts: [], ...extra,
})
const e = (from: string, to: string, kind: string) => ({ from, to, kind })

const T = '90_wiki/topics/t.md'
const MAP: ZenMap = {
  generated: '2026-10-19T00:00:00+02:00',
  nodes: [
    mk('10_ai/a.md', 'companion', '10_ai'),
    mk('10_ai/b.md', 'companion', '10_ai'),
    mk('11_research/n.md', 'note', '11_research'),
    mk('90_wiki/sources/a.md', 'wiki-source', null),
    mk('90_wiki/sources/b.md', 'wiki-source', null),
    mk(T, 'wiki-topic', null, { confidence: 'medium', conflicts: ['#c-0001'] }),
    mk('90_wiki/entities/e.md', 'wiki-entity', null, { confidence: 'low' }),
    mk('90_wiki/INDEX.md', 'wiki-meta', null),
    mk('10_ai/_originals/a.pdf', 'original', '10_ai'),
    mk('01_daily/d.md', 'note', '01_daily'),
    mk('tag:x', 'tag', null),
  ],
  edges: [
    e('90_wiki/sources/a.md', '10_ai/a.md', 'wiki'),
    e('90_wiki/sources/b.md', '10_ai/b.md', 'wiki'),
    e(T, '10_ai/a.md', 'wiki'),
    e(T, '90_wiki/sources/a.md', 'link'),
    e(T, '90_wiki/sources/b.md', 'link'),
    e(T, '90_wiki/entities/e.md', 'link'),
    e('10_ai/a.md', '10_ai/_originals/a.pdf', 'source'),
    e('01_daily/d.md', 'tag:x', 'tag'),
    ...['10_ai/a.md', '11_research/n.md', T, '90_wiki/entities/e.md', '01_daily/d.md'].map((t) => e('90_wiki/INDEX.md', t, 'link')),
  ],
}

const TOPIC = `---
title: t
---
> [!conflict] #c-0001 — open
> A: "x" — [a](../sources/a.md) (captured 2026-03-01)
> B: "y" — [b](../sources/b.md) (captured 2026-03-02)
> Decision: pending

> [!conflict] #c-0002 — resolved
> A: "x" — [a](../sources/a.md) (captured 2026-03-01)
> B: "y" — [n](../sources/n.md) (captured 2026-03-02)
> Decision: a
`
const read = (p: string) => (p === T ? TOPIC : '')

const graph = () => buildGraph(MAP, read).graph
const node = (id: string) => graph().nodes.find((n) => n.id === id)!
const edges = () => graph().edges.map((x) => [x.from, x.to, x.kind])

test('kinds and exclusions', () => {
  const { graph } = buildGraph(MAP, read)
  expect(graph.nodes.map(n => [n.id, n.kind]).sort()).toEqual([
    ['10_ai/a.md', 'source'], ['10_ai/b.md', 'source'], ['11_research/n.md', 'source'],
    ['90_wiki/entities/e.md', 'entity'], ['90_wiki/topics/t.md', 'topic']])
})
test('source page merges into its vault file', () => {
  const a = node('10_ai/a.md'); expect(a.wiki).toBe('90_wiki/sources/a.md'); expect(a.ingested).toBe(true)
  expect(node('11_research/n.md')).toMatchObject({ wiki: null, ingested: false })
})
test('edges: cites deduped across link and wiki, links, conflict between sources', () => {
  expect(edges()).toEqual(expect.arrayContaining([
    ['90_wiki/topics/t.md', '10_ai/a.md', 'cites'], ['90_wiki/topics/t.md', '10_ai/b.md', 'cites'],
    ['90_wiki/topics/t.md', '90_wiki/entities/e.md', 'links'], ['10_ai/a.md', '10_ai/b.md', 'conflict']]))
  expect(edges().filter(e => e[0] === '90_wiki/topics/t.md' && e[1] === '10_ai/a.md')).toHaveLength(1)
  expect(edges().some(e => e[0] === '90_wiki/INDEX.md')).toBe(false)
  expect(graph().edges.filter(e => e.kind === 'conflict')).toHaveLength(1) // resolved block draws nothing
})
test('clusters, inDegree, confidence', () => {
  expect(node('90_wiki/topics/t.md')).toMatchObject({ clusters: ['10_ai'], confidence: 'medium', conflicts: ['#c-0001'] })
  expect(node('10_ai/a.md').inDegree).toBe(1)
  expect(node('10_ai/a.md').confidence).toBeNull()
})
test('missing file drops the node and its edges with a warning', () => {
  const r = buildGraph(MAP, p => p === '90_wiki/entities/e.md' ? null : read(p))
  expect(r.warnings).toEqual(['missing on disk: 90_wiki/entities/e.md'])
  expect(r.graph.edges.some(e => e.to === '90_wiki/entities/e.md')).toBe(false)
})

describe('helpers', () => {
  test('conflict edge records the page and block parse is open-only', () => {
    expect(graph().edges.find((x) => x.kind === 'conflict')).toMatchObject({ conflict: '#c-0001', pages: [T] })
    expect(parseConflicts(T, TOPIC)).toEqual([{ id: '#c-0001', a: '90_wiki/sources/a.md', b: '90_wiki/sources/b.md' }])
  })
  test('owners maps wiki and vault paths to node ids', () => {
    const o = owners(graph())
    expect(o.get('90_wiki/sources/a.md')).toBe('10_ai/a.md')
    expect(o.get('10_ai/a.md')).toBe('10_ai/a.md')
    expect(o.get(T)).toBe(T)
  })
  test('resolvePath', () => {
    expect(resolvePath(T, '../sources/a.md')).toBe('90_wiki/sources/a.md')
    expect(resolvePath(T, '<../sources/a%20b.md#x?y>')).toBe('90_wiki/sources/a b.md')
    expect(resolvePath(T, '%E0%A4%A.md')).toBe('90_wiki/topics/%E0%A4%A.md')
    expect(resolvePath('a.md', './b.md')).toBe('b.md')
  })
})
