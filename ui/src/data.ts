import type { Graph } from './types'

export async function getGraph(): Promise<Graph> {
  const r = await fetch('data/graph.json')
  if (!r.ok) throw new Error(`graph.json: ${r.status}`)
  return r.json()
}

export async function getPage(path: string): Promise<string | null> {
  const r = await fetch('data/pages/' + path.split('/').map(encodeURIComponent).join('/'))
  return r.ok ? r.text() : null
}
