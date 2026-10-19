import { execFileSync } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, dirname, join, relative, resolve, sep } from 'node:path'
import { createInterface } from 'node:readline'
import { snapshot } from './snapshot.ts'
import type { Graph } from '../src/types.ts'

function realish(p: string): string {
  const abs = resolve(p)
  let head = abs
  const tail: string[] = []
  while (!existsSync(head) && dirname(head) !== head) {
    tail.unshift(basename(head))
    head = dirname(head)
  }
  return join(existsSync(head) ? realpathSync(head) : head, ...tail)
}

export function checkTarget(folder: string, repoRoot: string): string | null {
  const f = realish(folder)
  const root = realish(repoRoot)
  if (f === root || f.startsWith(root + sep)) return `export folder is inside the zen repo: ${folder}`
  if (existsSync(f)) {
    const entries = readdirSync(f).filter((e) => e !== '.git')
    if (entries.length > 0 && !existsSync(join(f, '.zen-export'))) {
      return `folder is not empty and not a previous ZEN export: ${folder}`
    }
  }
  return null
}

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
      const hit = rel.split(sep).some((s) => s.includes('_originals')) || e.name.startsWith('.env')
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

async function main(): Promise<void> {
  const positional = process.argv.slice(2).filter((a, i, all) => !a.startsWith('--') && all[i - 1] !== '--vault')
  if (positional.length < 1) {
    console.error('usage: node scripts/export.ts <folder> [--yes] [--vault ../vault]')
    process.exit(2)
  }
  const folder = resolve(process.env.ZEN_CALLER_CWD ?? process.cwd(), positional[0])
  const vault = resolve(arg('--vault', '../vault'))
  const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim()
  const refusal = checkTarget(folder, repoRoot)
  if (refusal) {
    console.error(refusal)
    process.exit(2)
  }

  const work = mkdtempSync(join(tmpdir(), 'zen-export-build-'))
  try {
    const publicDir = join(work, 'public')
    const r = snapshot(vault, join(publicDir, 'data'))
    for (const w of r.warnings) console.error(w)
    const graph = JSON.parse(readFileSync(join(publicDir, 'data', 'graph.json'), 'utf8')) as Graph
    const s = summarise(graph)
    for (const [c, n] of s.clusters) console.log(`  ${c}: ${n}`)
    console.log(`${s.nodes} nodes, ${s.pages} pages`)
    console.log('This exports the whole vault shown above, personal clusters included.')
    if (!process.argv.includes('--yes')) {
      process.stdout.write('Type yes to continue: ')
      if ((await readLine()).trim() !== 'yes') {
        console.error('aborted, nothing written')
        process.exit(1)
      }
    }

    const dist = join(work, 'dist')
    execFileSync('npx', ['vite', 'build', '--outDir', dist, '--emptyOutDir'], {
      stdio: 'inherit',
      env: { ...process.env, ZEN_PUBLIC_DIR: publicDir },
    })
    writeExport(dist, folder, { when: new Date().toISOString(), nodes: s.nodes, pages: s.pages })
  } finally {
    rmSync(work, { recursive: true, force: true })
  }

  const bad = forbidden(folder)
  if (bad.length > 0) {
    emptyKeepingGit(folder)
    console.error(`export contained forbidden paths, folder emptied:\n${bad.map((p) => `  ${p}`).join('\n')}`)
    process.exit(1)
  }
  const s = JSON.parse(readFileSync(join(folder, 'data', 'graph.json'), 'utf8')) as Graph
  const t = summarise(s)
  console.log(`exported ${t.nodes} nodes, ${t.pages} pages to ${folder}`)
  console.log('open it with GitHub Pages (Settings → Pages → Deploy from a branch → root)')
  console.log(`or locally: npx serve ${folder}`)
}

if (import.meta.main || process.argv[1]?.endsWith('export.ts')) await main()
