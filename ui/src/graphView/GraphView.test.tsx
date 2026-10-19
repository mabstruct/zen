import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { GNode, Graph } from '../types'
import { GraphView } from './GraphView'

afterEach(cleanup)

const n = (o: Partial<GNode>): GNode => ({
  id: 'x', title: 'X', kind: 'topic', clusters: ['10_a'], confidence: 'low', conflicts: [],
  updated: null, wiki: null, vault: null, ingested: true, inDegree: 0, ...o,
})
const G: Graph = {
  generated: '2026-10-19T00:00:00+00:00',
  nodes: [n({ id: 'topic', title: 'Topic' }), n({ id: 'ent', title: 'Entity', kind: 'entity' }), n({ id: 'src', title: 'Source', kind: 'source', confidence: null })],
  edges: [
    { from: 'topic', to: 'src', kind: 'cites' },
    { from: 'topic', to: 'ent', kind: 'links' },
    { from: 'ent', to: 'src', kind: 'conflict', conflict: 'c-1', pages: ['ent', 'src'] },
  ],
}

test('GraphView renders a node per page and reports clicks', async () => {
  const onSelect = vi.fn(); render(<GraphView graph={G} selected={null} onSelect={onSelect} />)
  expect(document.querySelectorAll('[data-node-id]')).toHaveLength(G.nodes.length)
  await userEvent.click(document.querySelector('[data-node-id="ent"]')!); expect(onSelect).toHaveBeenCalledWith('ent')
})
test('GraphView dims un-ingested sources and says so in the tooltip', async () => {
  const g: Graph = { ...G, nodes: [...G.nodes, n({ id: 'raw', title: 'Raw', kind: 'source', confidence: null, ingested: false })] }
  render(<GraphView graph={g} selected={null} onSelect={vi.fn()} />)
  const raw = document.querySelector('[data-node-id="raw"]')!
  expect(raw.getAttribute('data-ingested')).toBe('false')
  expect(raw.querySelector('rect')!.getAttribute('opacity')).toBe('0.35')
  expect(document.querySelector('[data-node-id="src"] rect')!.getAttribute('opacity')).toBe('1')
  await userEvent.hover(raw)
  expect(screen.getByText(/not ingested/)).toBeInTheDocument()
})
test('conflict edge click selects its first page; legend toggles a kind; find jumps', async () => {
  const onSelect = vi.fn(); const { getByText, getByPlaceholderText } = render(<GraphView graph={G} selected={null} onSelect={onSelect} />)
  await userEvent.click(document.querySelector('[data-edge-kind="conflict"]')!); expect(onSelect).toHaveBeenLastCalledWith('ent')
  await userEvent.click(getByText('source')); expect(document.querySelector('[data-node-id="src"]')).toBeNull()
  await userEvent.type(getByPlaceholderText('Find…'), 'enti{Enter}'); expect(onSelect).toHaveBeenLastCalledWith('ent')
})
