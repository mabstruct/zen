import type { Graph } from './types.ts'

export function owners(graph: Graph): Map<string, string> {
  const m = new Map<string, string>()
  for (const n of graph.nodes) {
    if (n.wiki !== null) m.set(n.wiki, n.id)
    if (n.vault !== null) m.set(n.vault, n.id)
  }
  return m
}

function normalize(p: string): string {
  const out: string[] = []
  for (const seg of p.split('/')) {
    if (seg === '' || seg === '.') continue
    if (seg === '..') out.pop()
    else out.push(seg)
  }
  return out.join('/')
}

export function resolvePath(from: string, href: string): string {
  let h = href.trim()
  if (h.startsWith('<') && h.endsWith('>')) h = h.slice(1, -1)
  h = h.replace(/[#?].*$/s, '')
  try {
    h = decodeURIComponent(h)
  } catch {
    /* keep the raw string */
  }
  if (h.startsWith('/')) return normalize(h)
  const dir = from.includes('/') ? from.slice(0, from.lastIndexOf('/')) : ''
  return normalize(dir ? `${dir}/${h}` : h)
}
