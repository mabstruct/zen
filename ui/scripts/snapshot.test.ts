import { afterEach, beforeEach, expect, test } from 'vitest'
import { cpSync, existsSync, globSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { snapshot } from './snapshot.ts'
import type { GNode } from '../src/types.ts'

const FIXTURE = resolve(import.meta.dirname, '../test/fixture-vault')
let tmp: string
let tmpVault: string

beforeEach(() => {
  tmp = mkdtempSync(join(tmpdir(), 'zen-snap-out-'))
  tmpVault = mkdtempSync(join(tmpdir(), 'zen-snap-vault-'))
})
afterEach(() => {
  rmSync(tmp, { recursive: true, force: true })
  rmSync(tmpVault, { recursive: true, force: true })
})

function copyFixtureTo(dir: string): string {
  cpSync(FIXTURE, dir, { recursive: true })
  return dir
}

test('writes graph and pages, never originals', () => {
  const r = snapshot(FIXTURE, tmp)
  expect(r.nodes).toBe(6)
  expect(existsSync(join(tmp, 'pages/10_ai/attn.md'))).toBe(true)
  expect(existsSync(join(tmp, 'pages/90_wiki/sources/attn.md'))).toBe(true)
  expect(globSync('**/*', { cwd: tmp }).some((p) => p.includes('_originals'))).toBe(false)
  expect(existsSync(join(tmp, 'pages/01_daily'))).toBe(false)
})
test('stale map: file gone on disk is dropped with a warning', () => {
  const v = copyFixtureTo(tmpVault)
  rmSync(join(v, '90_wiki/entities/vaswani.md'))
  const r = snapshot(v, tmp)
  expect(r.warnings).toContain('missing on disk: 90_wiki/entities/vaswani.md')
  expect(JSON.parse(readFileSync(join(tmp, 'graph.json'), 'utf8')).nodes.some((n: GNode) => n.id.endsWith('vaswani.md'))).toBe(false)
})
test('re-run empties out first', () => {
  writeFileSync(join(tmp, 'stale.txt'), 'x')
  snapshot(FIXTURE, tmp)
  expect(existsSync(join(tmp, 'stale.txt'))).toBe(false)
})
