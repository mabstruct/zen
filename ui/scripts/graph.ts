import { owners, resolvePath } from '../src/graph.ts'
import type { Graph, GEdge, GNode, Kind, MapNode, ZenMap } from '../src/types.ts'

const WIKI_KIND: Record<string, Kind> = {
  'wiki-topic': 'topic',
  'wiki-entity': 'entity',
  'wiki-synthesis': 'synthesis',
}

export interface ConflictBlock {
  id: string
  a: string | null
  b: string | null
}

export function parseConflicts(pagePath: string, text: string): ConflictBlock[] {
  const out: ConflictBlock[] = []
  const lines = text.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const m = /^>\s*\[!conflict\]\s+(#c-\d+)\s+\S+\s+open\b/.exec(lines[i])
    if (!m) continue
    let a: string | null = null
    let b: string | null = null
    for (let j = i + 1; j < lines.length && lines[j].startsWith('>'); j++) {
      const side = /^>\s*([AB]):/.exec(lines[j])
      if (!side) continue
      const link = /\]\(([^)\s]*sources\/[^)\s]*)\)/.exec(lines[j])
      const target = link ? resolvePath(pagePath, link[1]) : null
      if (side[1] === 'A') a = target
      else b = target
    }
    out.push({ id: m[1], a, b })
  }
  return out
}

export function buildGraph(
  map: ZenMap,
  readText: (path: string) => string | null,
): { graph: Graph; warnings: string[] } {
  const warnings: string[] = []
  const byId = new Map<string, MapNode>(map.nodes.map((n) => [n.id, n]))
  const warned = new Set<string>()
  const exists = (p: string): boolean => {
    if (readText(p) !== null) return true
    if (!warned.has(p)) {
      warned.add(p)
      warnings.push(`missing on disk: ${p}`)
    }
    return false
  }

  const nodes = new Map<string, GNode>()
  const base = (id: string, n: MapNode, kind: Kind): GNode => ({
    id, title: n.title, kind, clusters: [], confidence: null, conflicts: [],
    updated: n.updated, wiki: null, vault: null, ingested: false, inDegree: 0,
  })

  for (const n of map.nodes) {
    if (n.path === null) continue
    if (n.type in WIKI_KIND) {
      if (!exists(n.path)) continue
      const g = base(n.id, n, WIKI_KIND[n.type])
      g.wiki = n.path
      g.ingested = true
      g.confidence = n.confidence
      g.conflicts = n.conflicts
      nodes.set(n.id, g)
    } else if ((n.type === 'companion' || n.type === 'note') && /^1\d_/.test(n.cluster ?? '')) {
      if (!exists(n.path)) continue
      const g = base(n.id, n, 'source')
      g.vault = n.path
      g.clusters = [n.cluster!]
      nodes.set(n.id, g)
    }
  }

  for (const e of map.edges) {
    if (e.kind !== 'wiki') continue
    const from = byId.get(e.from)
    const target = nodes.get(e.to)
    if (from?.type !== 'wiki-source' || !target || target.kind !== 'source' || from.path === null) continue
    if (!exists(from.path)) continue
    target.wiki = from.path
    target.ingested = true
    target.confidence = null
    target.conflicts = from.conflicts
  }

  const gnodes = [...nodes.values()].sort((a, b) => (a.id < b.id ? -1 : 1))
  const graph: Graph = { generated: map.generated, nodes: gnodes, edges: [] }
  const own = owners(graph)

  const edges = new Map<string, GEdge>()
  for (const e of map.edges) {
    if (e.kind !== 'link' && e.kind !== 'wiki') continue
    if (byId.get(e.from)?.type === 'wiki-meta') continue
    const from = own.get(e.from)
    const to = own.get(e.to)
    if (from === undefined || to === undefined || from === to) continue
    const fromWiki = nodes.get(from)!.kind !== 'source'
    const kind = fromWiki && nodes.get(to)!.kind === 'source' ? 'cites' : 'links'
    edges.set(`${from}\0${to}\0${kind}`, { from, to, kind })
  }

  const conflicts = new Map<string, GEdge>()
  for (const n of gnodes) {
    if (n.wiki === null) continue
    const text = readText(n.wiki)
    if (!text) continue
    for (const c of parseConflicts(n.wiki, text)) {
      const a = c.a === null ? undefined : own.get(c.a)
      const b = c.b === null ? undefined : own.get(c.b)
      if (a === undefined || b === undefined || a === b) continue
      if (nodes.get(a)!.kind !== 'source' || nodes.get(b)!.kind !== 'source') continue
      const [x, y] = a < b ? [a, b] : [b, a]
      const key = `${x}\0${y}\0${c.id}`
      const prior = conflicts.get(key)
      if (prior) {
        if (!prior.pages!.includes(n.wiki)) prior.pages!.push(n.wiki)
      } else {
        conflicts.set(key, { from: a, to: b, kind: 'conflict', conflict: c.id, pages: [n.wiki] })
      }
    }
  }

  const all = [...edges.values(), ...conflicts.values()]
  for (const e of all) {
    if (e.kind !== 'conflict') nodes.get(e.to)!.inDegree++
  }
  for (const n of gnodes) {
    if (n.kind === 'source') continue
    const cl = new Set<string>()
    for (const e of all) {
      if (e.kind === 'cites' && e.from === n.id) nodes.get(e.to)!.clusters.forEach((c) => cl.add(c))
    }
    n.clusters = [...cl].sort()
  }
  graph.edges = all
  return { graph, warnings }
}
