import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, realpathSync } from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'

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

if (import.meta.main || process.argv[1]?.endsWith('check-target.ts')) {
  const folder = process.argv[2]
  if (!folder) {
    console.error('usage: node scripts/check-target.ts <folder>')
    process.exit(2)
  }
  const repoRoot = execFileSync('git', ['rev-parse', '--show-toplevel'], { encoding: 'utf8' }).trim()
  const refusal = checkTarget(resolve(folder), repoRoot)
  if (refusal) {
    console.error(refusal)
    process.exit(2)
  }
}
