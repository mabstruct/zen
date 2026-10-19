import type { GNode, Graph, Kind } from '../types'

export const KINDS: Kind[] = ['topic', 'entity', 'synthesis', 'source']

const BASE = { low: 6, medium: 10, high: 14 }

export function nodeRadius(n: GNode): number {
  if (n.kind === 'source') return 7
  return BASE[n.confidence ?? 'low'] + Math.min(3.5, 1.5 * Math.log2(1 + n.inDegree))
}

export function nodeColour(n: GNode, mode: 'kind' | 'cluster'): string {
  if (mode === 'kind') return `var(--color-kind-${n.kind})`
  const c = n.clusters[0] ?? ''
  let h = 0
  for (const ch of c) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return `var(--color-cluster-${h % 8})`
}

export function neighbourhood(g: Graph, id: string): Set<string> {
  const s = new Set([id])
  for (const e of g.edges) {
    if (e.from === id) s.add(e.to)
    else if (e.to === id) s.add(e.from)
  }
  return s
}

export function visible(g: Graph, hidden: Set<Kind>): Graph {
  const nodes = g.nodes.filter(n => !hidden.has(n.kind))
  const ids = new Set(nodes.map(n => n.id))
  return { ...g, nodes, edges: g.edges.filter(e => ids.has(e.from) && ids.has(e.to)) }
}

const fold = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()

export function findByTitle(nodes: GNode[], q: string): GNode | null {
  const f = fold(q.trim())
  if (!f) return null
  const hits = nodes.map(n => ({ n, t: fold(n.title) })).filter(x => x.t.includes(f))
  if (!hits.length) return null
  const starts = hits.filter(x => x.t.startsWith(f))
  const pool = starts.length ? starts : hits
  return pool.reduce((a, b) => (b.t.length < a.t.length ? b : a)).n
}
