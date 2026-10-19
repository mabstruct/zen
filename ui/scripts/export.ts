import { execFileSync } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, dirname, join, relative, resolve, sep } from 'node:path'
import { createInterface } from 'node:readline'
import { checkTarget } from './check-target.ts'
import { snapshot } from './snapshot.ts'
import type { Graph } from '../src/types.ts'

export { checkTarget }

export function summarise(graph: Graph): { clusters: [string, number][]; nodes: number; pages: number } {
  const counts = new Map<string, number>()
  const paths = new Set<string>()
  for (const n of graph.nodes) {
    if (n.kind === 'source' && n.clusters[0]) counts.set(n.clusters[0], (counts.get(n.clusters[0]) ?? 0) + 1)
    if (n.wiki) paths.add(n.wiki)
    if (n.vault) paths.add(n.vault)
  }
  const clusters = [...counts.entries()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
  return { clusters, nodes: graph.nodes.length, pages: paths.size }
}

function emptyKeepingGit(folder: string): void {
  mkdirSync(folder, { recursive: true })
  for (const e of readdirSync(folder)) if (e !== '.git') rmSync(join(folder, e), { recursive: true, force: true })
}

export function writeExport(dist: string, folder: string, info: { when: string; nodes: number; pages: number }): void {
  emptyKeepingGit(folder)
  cpSync(dist, folder, { recursive: true })
  writeFileSync(join(folder, '.nojekyll'), '')
  writeFileSync(join(folder, '.zen-export'), info.when + '\n')
  writeFileSync(
    join(folder, 'README.md'),
    `# ZEN export

Exported ${info.when}: ${info.nodes} nodes, ${info.pages} pages.

Publishing this folder is the owner's decision; it contains every page of the vault it was exported from.

## How to open it

- GitHub Pages: Settings → Pages → Deploy from a branch → root.
- Locally: \`npx serve .\`

Opening index.html directly from disk does not work.
`,
  )
}

export function forbidden(folder: string): string[] {
  const out: string[] = []
  const walk = (dir: string): void => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === '.git' && dir === folder) continue
      const full = join(dir, e.name)
      const rel = relative(folder, full)
      const hit = rel.split(sep).some((s) => s.includes('_originals') || s.startsWith('.env'))
      if (e.isDirectory() && readdirSync(full).length > 0) walk(full)
      else if (hit) out.push(rel)
    }
  }
  walk(folder)
  return out
}

function arg(name: string, fallback: string): string {
  const i = process.argv.indexOf(name)
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback
}

async function readLine(): Promise<string> {
  const rl = createInterface({ input: process.stdin })
  return new Promise((res) => {
    rl.once('line', (l) => { rl.close(); res(l) })
    rl.once('close', () => res(''))
  })
}

export function localIso(d: Date = new Date()): string {
  const p = (n: number, w = 2): string => String(n).padStart(w, '0')
  const off = -d.getTimezoneOffset()
  const sign = off >= 0 ? '+' : '-'
  return (
    `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}` +
    `${sign}${p(Math.floor(Math.abs(off) / 60))}:${p(Math.abs(off) % 60)}`
  )
}

export interface RunOptions {
  folder: string
  vault: string
  repoRoot: string
  yes: boolean
  confirm: () => Promise<string>
  tmpRoot: string
}

export async function run(o: RunOptions): Promise<number> {
  const refusal = checkTarget(o.folder, o.repoRoot)
  if (refusal) {
    console.error(refusal)
    return 2
  }
  const work = mkdtempSync(join(o.tmpRoot, 'zen-export-build-'))
  let wrote = false
  try {
    const publicDir = join(work, 'public')
    const r = snapshot(o.vault, join(publicDir, 'data'))
    for (const w of r.warnings) console.error(w)
    const graph = JSON.parse(readFileSync(join(publicDir, 'data', 'graph.json'), 'utf8')) as Graph
    const s = summarise(graph)
    for (const [c, n] of s.clusters) console.log(`  ${c}: ${n}`)
    console.log(`${s.nodes} nodes, ${s.pages} pages`)
    console.log('This exports the whole vault shown above, personal clusters included.')
    if (!o.yes) {
      process.stdout.write('Type yes to continue: ')
      if ((await o.confirm()).replace(/\r?\n$/, '') !== 'yes') {
        console.error('aborted, nothing written')
        return 1
      }
    }
    const dist = join(work, 'dist')
    execFileSync('npx', ['vite', 'build', '--outDir', dist, '--emptyOutDir'], {
      stdio: 'inherit',
      env: { ...process.env, ZEN_PUBLIC_DIR: publicDir },
    })
    wrote = true
    writeExport(dist, o.folder, { when: localIso(), nodes: s.nodes, pages: s.pages })
    const bad = forbidden(o.folder)
    if (bad.length > 0) {
      emptyKeepingGit(o.folder)
      console.error(`export contained forbidden paths, folder emptied:\n${bad.map((p) => `  ${p}`).join('\n')}`)
      return 1
    }
    console.log(`exported ${s.nodes} nodes, ${s.pages} pages to ${o.folder}`)
    console.log('open it with GitHub Pages (Settings → Pages → Deploy from a branch → root)')
    console.log(`or locally: npx serve ${o.folder}`)
    return 0
  } catch (e) {
    if (wrote) emptyKeepingGit(o.folder)
    console.error(e instanceof Error ? e.message : String(e))
    return 1
  } finally {
    rmSync(work, { recursive: true, force: true })
  }
}

if (import.meta.main || process.argv[1]?.endsWith('export.ts')) {
  const positional = process.argv.slice(2).filter((a, i, all) => !a.startsWith('--') && all[i - 1] !== '--vault')
  if (positional.length < 1) {
    console.error('usage: node scripts/export.ts <folder> [--yes] [--vault ../vault]')
    process.exitCode = 2
  } else {
    process.exitCode = await run({
      folder: resolve(positional[0]),
      vault: resolve(arg('--vault', '../vault')),
      repoRoot: execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim(),
      yes: process.argv.includes('--yes'),
      confirm: readLine,
      tmpRoot: tmpdir(),
    })
  }
}
