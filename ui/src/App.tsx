import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { getGraph } from './data'
import { owners as buildOwners } from './graph'
import { GraphView } from './graphView/GraphView'
import { parseHash, toHash } from './markdown'
import { Reader } from './reader/Reader'
import { pushTrail } from './trail'
import type { Graph } from './types'

export default function App() {
  const [graph, setGraph] = useState<Graph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [path, setPath] = useState<string | null>(() => parseHash(location.hash).path)
  const [trail, setTrail] = useState<string[]>(() => {
    const p = parseHash(location.hash).path
    return p ? [p] : []
  })
  const ownersRef = useRef(new Map<string, string>())
  const [open, setOpen] = useState(true)

  useEffect(() => {
    getGraph().then(setGraph, e => setError(String(e)))
  }, [])

  useEffect(() => {
    const onHash = () => {
      const p = parseHash(location.hash).path
      setPath(p)
      if (p) setTrail(t => pushTrail(t, p, ownersRef.current))
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const owners = useMemo(() => (graph ? buildOwners(graph) : new Map<string, string>()), [graph])
  ownersRef.current = owners
  const navigate = useCallback((p: string) => { location.hash = toHash(p) }, [])
  const select = useCallback((x: string) => {
    const node = graph?.nodes.find(n => n.id === (owners.get(x) ?? x))
    if (!node) return
    const target = node.kind === 'source' ? node.vault : node.wiki ?? node.vault
    if (target) navigate(target)
  }, [graph, owners, navigate])
  const reset = () => {
    setTrail([])
    setPath(null)
    location.hash = '#/'
  }

  if (error) return <div className="p-4 text-conflict">Could not load the graph: {error}</div>
  if (!graph) return <div className="p-4 text-muted">Loading…</div>

  const title = (p: string) => graph.nodes.find(n => n.id === owners.get(p))?.title ?? p
  const selected = path ? owners.get(path) ?? null : null

  return (
    <div className="flex h-full">
      <main className="relative min-w-0 flex-1">
        <GraphView graph={graph} selected={selected} onSelect={select} onReset={reset} />
      </main>
      <aside className={`flex flex-col border-l border-border bg-surface ${open ? 'w-[34rem]' : 'w-10'}`}>
        <button onClick={() => setOpen(o => !o)} aria-label={open ? 'Collapse reader' : 'Expand reader'} className="p-2 text-left text-muted">
          {open ? '›' : '‹'}
        </button>
        {open && (
          <>
            <nav data-testid="trail" className="flex flex-wrap gap-1 border-b border-border px-4 pb-2 text-xs text-muted">
              {trail.map((p, i) => (
                <span key={i}>
                  {i > 0 && ' › '}
                  <a href={toHash(p)} className="hover:text-accent">{title(p)}</a>
                </span>
              ))}
            </nav>
            <div className="min-h-0 flex-1 overflow-y-auto">
              {path && <Reader graph={graph} owners={owners} path={path} onNavigate={navigate} />}
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
