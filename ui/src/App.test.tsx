import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { GNode, Graph } from './types'
import App from './App'

const n = (o: Partial<GNode>): GNode => ({
  id: 'x', title: 'X', kind: 'topic', clusters: ['10_x'], confidence: null, conflicts: [],
  updated: null, wiki: null, vault: null, ingested: true, inDegree: 0, ...o,
})
const G: Graph = {
  generated: '2026-10-19T00:00:00+00:00',
  nodes: [
    n({ id: '10_x/a.md', title: 'Ingested', kind: 'source', wiki: 'w/a.md', vault: '10_x/a.md' }),
    n({ id: '10_x/b.md', title: 'Raw', kind: 'source', vault: '10_x/b.md', ingested: false }),
    n({ id: 'w/t.md', title: 'Topic', wiki: 'w/t.md' }),
  ],
  edges: [{ from: 'w/t.md', to: '10_x/b.md', kind: 'conflict', conflict: 'c-1', pages: ['w/a.md', 'w/t.md'] }],
}
vi.mock('./data', () => ({ getGraph: vi.fn(async () => G), getPage: vi.fn(async () => '') }))
beforeEach(() => { location.hash = '#/' })
afterEach(cleanup)

const hash = () => decodeURIComponent(location.hash)

test('source click opens the wiki summary when ingested, the text when not', async () => {
  render(<App />)
  await screen.findByPlaceholderText('Find…')
  await userEvent.click(document.querySelector('[data-node-id="10_x/a.md"]')!)
  expect(hash()).toBe('#/p/w/a.md')
  await userEvent.click(document.querySelector('[data-node-id="10_x/b.md"]')!)
  expect(hash()).toBe('#/p/10_x/b.md')
})

test('conflict edge click opens the conflict page itself, even a wiki-source page', async () => {
  render(<App />)
  await screen.findByPlaceholderText('Find…')
  await userEvent.click(document.querySelector('[data-edge-kind="conflict"]')!)
  expect(hash()).toBe('#/p/w/a.md')
})
