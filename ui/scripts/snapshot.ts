import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { buildGraph } from './graph.ts'
import type { ZenMap } from '../src/types.ts'

export function snapshot(
  vault: string,
  out: string,
): { nodes: number; edges: number; pages: number; warnings: string[] } {
  const mapPath = join(vault, '_meta', 'map.json')
  if (!existsSync(mapPath)) throw new Error('no map.json — run zen-index first')
  const map = JSON.parse(readFileSync(mapPath, 'utf8')) as ZenMap
  const readText = (p: string): string | null => {
    const full = join(vault, p)
    return existsSync(full) ? readFileSync(full, 'utf8') : null
  }
  const { graph, warnings } = buildGraph(map, readText)

  const paths = new Set<string>()
  for (const n of graph.nodes) {
    if (n.wiki) paths.add(n.wiki)
    if (n.vault) paths.add(n.vault)
  }
  for (const p of paths) {
    if (`/${p}`.includes('/_originals/')) throw new Error(`refusing to copy original: ${p}`)
  }

  rmSync(out, { recursive: true, force: true })
  mkdirSync(out, { recursive: true })
  writeFileSync(join(out, 'graph.json'), JSON.stringify(graph, null, 2) + '\n')
  for (const p of paths) {
    const dest = join(out, 'pages', p)
    mkdirSync(dirname(dest), { recursive: true })
    copyFileSync(join(vault, p), dest)
  }
  return { nodes: graph.nodes.length, edges: graph.edges.length, pages: paths.size, warnings }
}

function arg(name: string, fallback: string): string {
  const i = process.argv.indexOf(name)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback
}

if (import.meta.main || process.argv[1]?.endsWith('snapshot.ts')) {
  const vault = resolve(arg('--vault', '../vault'))
  const out = resolve(arg('--out', 'public/data'))
  if (!existsSync(join(vault, '_meta', 'map.json'))) {
    console.error('no map.json — run zen-index first')
    process.exit(1)
  }
  const r = snapshot(vault, out)
  for (const w of r.warnings) console.error(w)
  console.log(`snapshot: ${r.nodes} nodes, ${r.edges} edges, ${r.pages} pages`)
}
