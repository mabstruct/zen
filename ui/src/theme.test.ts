import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { KINDS } from './graphView/style'

const css = readFileSync('src/index.css', 'utf8')

test('index.css keeps every colour variable the graph can use', () => {
  expect(css).toMatch(/@theme static/)
  const vars = [...KINDS.map(k => `--color-kind-${k}`), ...Array.from({ length: 8 }, (_, i) => `--color-cluster-${i}`), '--color-conflict', '--color-edge', '--color-text']
  for (const v of vars) expect(css).toContain(`${v}:`)
})
