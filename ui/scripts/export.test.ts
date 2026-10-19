import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { checkTarget, forbidden, run, summarise, writeExport } from './export.ts'
import type { Graph } from '../src/types.ts'

const REPO = '/some/where/zen'
let tmpA: string, tmpB: string, tmpC: string, DIST_FIXTURE: string

beforeEach(() => {
  const base = mkdtempSync(join(tmpdir(), 'zen-export-test-'))
  tmpA = join(base, 'a'); tmpB = join(base, 'b'); tmpC = join(base, 'c'); DIST_FIXTURE = join(base, 'dist')
  for (const d of [tmpA, tmpB, tmpC, join(DIST_FIXTURE, 'data')]) mkdirSync(d, { recursive: true })
  writeFileSync(join(DIST_FIXTURE, 'index.html'), '<html></html>')
  writeFileSync(join(DIST_FIXTURE, 'data/graph.json'), '{}')
})

describe('export', () => {
  test('refuses a folder inside the repo', () => {
    expect(checkTarget(join(REPO, 'out'), REPO)).toMatch(/inside the zen repo/)
    expect(checkTarget(REPO, REPO)).toMatch(/inside the zen repo/)
  })
  test('refuses a foreign non-empty folder, accepts empty, git-only, or a previous export', () => {
    writeFileSync(join(tmpA, 'mine.txt'), 'x'); expect(checkTarget(tmpA, REPO)).toMatch(/not a previous ZEN export/)
    mkdirSync(join(tmpB, '.git')); expect(checkTarget(tmpB, REPO)).toBeNull()
    writeFileSync(join(tmpC, '.zen-export'), 't'); writeFileSync(join(tmpC, 'old.html'), ''); expect(checkTarget(tmpC, REPO)).toBeNull()
  })
  test('writeExport keeps .git, replaces the rest, writes markers and README', () => {
    mkdirSync(join(tmpB, '.git')); writeFileSync(join(tmpB, '.git', 'HEAD'), 'ref'); writeFileSync(join(tmpB, 'stale.html'), '')
    writeExport(DIST_FIXTURE, tmpB, { when: '2026-10-19T12:00:00+02:00', nodes: 6, pages: 8 })
    expect(existsSync(join(tmpB, '.git/HEAD'))).toBe(true); expect(existsSync(join(tmpB, 'stale.html'))).toBe(false)
    for (const f of ['.nojekyll', '.zen-export', 'README.md', 'index.html']) expect(existsSync(join(tmpB, f))).toBe(true)
    expect(readFileSync(join(tmpB, 'README.md'), 'utf8')).toContain("Publishing this folder is the owner's decision")
  })
  test('forbidden finds originals and env files but ignores .git', () => {
    mkdirSync(join(tmpA, 'data/pages/10_ai/_originals'), { recursive: true }); writeFileSync(join(tmpA, 'data/pages/10_ai/_originals/a.pdf'), '')
    writeFileSync(join(tmpA, '.env.local'), ''); mkdirSync(join(tmpA, '.git')); writeFileSync(join(tmpA, '.git/.env'), '')
    expect(forbidden(tmpA).sort()).toEqual(['.env.local', 'data/pages/10_ai/_originals/a.pdf'])
  })
  test('summarise counts clusters by source nodes and distinct pages', () => {
    const g = {
      nodes: [
        { id: 'a', kind: 'source', clusters: ['11_b'], wiki: 'w/a.md', vault: '11_b/a.md' },
        { id: 'b', kind: 'source', clusters: ['10_a'], vault: '10_a/b.md' },
        { id: 'c', kind: 'source', clusters: ['10_a'], wiki: 'w/a.md' },
        { id: 'd', kind: 'topic', clusters: ['10_a'], wiki: 'w/d.md' },
      ],
      edges: [],
    } as unknown as Graph
    expect(summarise(g)).toEqual({ clusters: [['10_a', 2], ['11_b', 1]], nodes: 4, pages: 4 })
  })
  test('forbidden flags any path with a .env segment', () => {
    mkdirSync(join(tmpA, '.env.d'), { recursive: true }); writeFileSync(join(tmpA, '.env.d/x.txt'), '')
    expect(forbidden(tmpA)).toEqual(['.env.d/x.txt'])
  })
  test('an aborted run writes nothing and leaves no temp dir', async () => {
    const tmpRoot = join(tmpA, 'tmp'); mkdirSync(tmpRoot)
    const folder = join(tmpA, 'out')
    const code = await run({ folder, vault: join(process.cwd(), 'test/fixture-vault'), repoRoot: REPO, yes: false, confirm: async () => 'no', tmpRoot })
    expect(code).toBe(1)
    expect(readdirSync(tmpRoot)).toEqual([])
    expect(existsSync(folder)).toBe(false)
  })
})
