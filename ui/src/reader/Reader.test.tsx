import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { GNode, Graph } from '../types'
import { owners } from '../graph'
import { Reader } from './Reader'

vi.mock('../data', () => ({
  getPage: vi.fn(async (p: string) => {
    if (p === 'wiki/t.md') return '---\ntitle: T\n---\nSee [src](a.md) and [b](../10_x/b.md).\n'
    if (p === 'wiki/a.md') return '---\ntitle: A\n---\nWiki summary body.\n'
    if (p === '10_x/a.md') return '---\ntitle: A\n---\n## Summary\nCompanion summary.\n\n## Extracted text\nRAW TEXT\n'
    if (p === '10_x/b.md') return '## Summary\nB summary.\n'
    return null
  }),
}))
afterEach(cleanup)

const n = (o: Partial<GNode>): GNode => ({
  id: 'x', title: 'X', kind: 'topic', clusters: ['10_x'], confidence: 'high', conflicts: [],
  updated: '2026-10-01T00:00:00+00:00', wiki: null, vault: null, ingested: true, inDegree: 0, ...o,
})
const G: Graph = {
  generated: '2026-10-19T00:00:00+00:00',
  nodes: [
    n({ id: 'wiki/t.md', title: 'Topic T', wiki: 'wiki/t.md', conflicts: ['#c-1'] }),
    n({ id: '10_x/a.md', title: 'Source A', kind: 'source', confidence: null, wiki: 'wiki/a.md', vault: '10_x/a.md' }),
    n({ id: '10_x/b.md', title: 'Source B', kind: 'source', confidence: null, vault: '10_x/b.md', ingested: false }),
  ],
  edges: [],
}
const O = owners(G)

test('Reader: unknown path', async () => {
  render(<Reader graph={G} owners={O} path="nope.md" onNavigate={vi.fn()} />)
  expect(await screen.findByText(/Not in this snapshot: nope\.md/)).toBeInTheDocument()
})

test('Reader: header shows title and open conflicts', async () => {
  render(<Reader graph={G} owners={O} path="wiki/t.md" onNavigate={vi.fn()} />)
  expect(await screen.findByRole('heading', { level: 1, name: 'Topic T' })).toBeInTheDocument()
  expect(screen.getByText(/#c-1/)).toBeInTheDocument()
})

test('Reader: un-ingested source opens on Text; ingested source link opens Wiki summary', async () => {
  const nav = vi.fn()
  const { unmount } = render(<Reader graph={G} owners={O} path="10_x/b.md" onNavigate={nav} />)
  expect(await screen.findByText('B summary.')).toBeInTheDocument()
  expect(screen.getByRole('tab', { name: 'Text' })).toHaveAttribute('aria-selected', 'true')
  unmount()
  render(<Reader graph={G} owners={O} path="wiki/a.md" onNavigate={nav} />)
  expect(await screen.findByText('Wiki summary body.')).toBeInTheDocument()
  expect(screen.getByRole('tab', { name: 'Wiki summary' })).toHaveAttribute('aria-selected', 'true')
  await userEvent.click(screen.getByRole('tab', { name: 'Text' }))
  expect(nav).toHaveBeenCalledWith('10_x/a.md')
})

test('Reader: un-ingested source is labelled, sources show no confidence dots', async () => {
  render(<Reader graph={G} owners={O} path="10_x/b.md" onNavigate={vi.fn()} />)
  expect(await screen.findByText('not ingested')).toBeInTheDocument()
  expect(screen.queryByLabelText(/confidence/)).toBeNull()
})

test('Reader: companion shows summary with extracted text collapsed', async () => {
  render(<Reader graph={G} owners={O} path="10_x/a.md" onNavigate={vi.fn()} />)
  expect(await screen.findByText('Companion summary.')).toBeInTheDocument()
  expect(document.querySelector('details')).not.toHaveAttribute('open')
})

test('Reader: clicking an in-app link calls onNavigate with the resolved path', async () => {
  const nav = vi.fn()
  render(<Reader graph={G} owners={O} path="wiki/t.md" onNavigate={nav} />)
  await userEvent.click(await screen.findByRole('link', { name: 'src' }))
  expect(nav).toHaveBeenCalledWith('wiki/a.md')
})
