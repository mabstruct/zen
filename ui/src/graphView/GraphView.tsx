import { useEffect, useMemo, useRef, useState } from 'react'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation } from 'd3-force'
import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3-force'
import { zoom, zoomIdentity } from 'd3-zoom'
import type { ZoomBehavior } from 'd3-zoom'
import { drag } from 'd3-drag'
import { select } from 'd3-selection'
import type { GEdge, GNode, Graph, Kind } from '../types'
import { Controls, Legend } from './Controls'
import { findByTitle, neighbourhood, nodeColour, nodeRadius, visible } from './style'

const hasView = (e: Event & { view?: unknown }) => !!e.view && !(e as MouseEvent).ctrlKey && !(e as MouseEvent).button
const W = 1000
const H = 700
type SNode = GNode & SimulationNodeDatum
type SLink = SimulationLinkDatum<SNode> & { edge: GEdge }

function layout(graph: Graph): { nodes: SNode[]; links: SLink[] } {
  const nodes: SNode[] = graph.nodes.map(n => ({ ...n }))
  const links: SLink[] = graph.edges.map(edge => ({ source: edge.from, target: edge.to, edge }))
  const sim = forceSimulation(nodes)
    .force('link', forceLink<SNode, SLink>(links).id(d => d.id).distance(l => (l.edge.kind === 'conflict' ? 120 : 55)).strength(l => (l.edge.kind === 'conflict' ? 0.02 : 0.15)))
    .force('charge', forceManyBody().strength(-140).distanceMax(400))
    .force('collide', forceCollide<SNode>(d => nodeRadius(d) + 2))
    .force('centre', forceCenter(W / 2, H / 2))
    .stop()
  for (let i = 0; i < 300; i++) sim.tick()
  return { nodes, links }
}

export function GraphView({ graph, selected, onSelect, onReset }: { graph: Graph; selected: string | null; onSelect: (id: string) => void; onReset?: () => void }) {
  const [hidden, setHidden] = useState<Set<Kind>>(new Set())
  const [labels, setLabels] = useState(true)
  const [colourMode, setColourMode] = useState<'kind' | 'cluster'>('kind')
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null)
  const [transform, setTransform] = useState(zoomIdentity)
  const [, bump] = useState(0)
  const svgRef = useRef<SVGSVGElement>(null)
  const zoomRef = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const nodesRef = useRef<Map<string, SNode>>(new Map())

  const laid = useMemo(() => layout(graph), [graph])
  nodesRef.current = new Map(laid.nodes.map(n => [n.id, n]))
  const vis = useMemo(() => visible({ ...graph, nodes: laid.nodes, edges: graph.edges }, hidden), [graph, laid, hidden])
  const links = laid.links.filter(l => !hidden.has((l.source as SNode).kind) && !hidden.has((l.target as SNode).kind))
  const near = useMemo(() => (hover ? neighbourhood(graph, hover.id) : null), [graph, hover])
  const sources = useMemo(() => {
    const m = new Map<string, number>()
    for (const e of graph.edges) if (e.kind === 'cites') m.set(e.from, (m.get(e.from) ?? 0) + 1)
    return m
  }, [graph])

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const z = zoom<SVGSVGElement, unknown>().filter(e => hasView(e) || e.type === 'wheel').scaleExtent([0.2, 6]).extent([[0, 0], [W, H]]).on('zoom', e => setTransform(e.transform))
    zoomRef.current = z
    select(svg).call(z).on('dblclick.zoom', null)
    return () => { select(svg).on('.zoom', null) }
  }, [])

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    select(svg).selectAll<SVGGElement, SNode>('g[data-node-id]').each(function () {
      const id = this.getAttribute('data-node-id')!
      select<SVGGElement, unknown>(this).call(
        drag<SVGGElement, unknown>().filter(hasView).clickDistance(4)
          .on('drag', e => {
            const n = nodesRef.current.get(id)
            if (n) { n.x = e.x; n.y = e.y; bump(v => v + 1) }
          }),
      )
    })
  })

  const fitTarget = () => {
    const ns = laid.nodes.filter(n => n.x != null && n.y != null)
    if (ns.length === 0) return { k: 1, x: 0, y: 0 }
    const xs = ns.map(n => n.x!), ys = ns.map(n => n.y!)
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys)
    const pad = 40
    const k = Math.min(W / (x1 - x0 + 2 * pad), H / (y1 - y0 + 2 * pad), 2)
    return { k, x: W / 2 - (k * (x0 + x1)) / 2, y: H / 2 - (k * (y0 + y1)) / 2 }
  }

  useEffect(() => {
    const svg = svgRef.current, z = zoomRef.current
    if (!svg || !z) return
    const f = fitTarget()
    select(svg).call(z.transform, zoomIdentity.translate(f.x, f.y).scale(f.k))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [laid])

  const moveTo = (t: { k: number; x: number; y: number }) => {
    const svg = svgRef.current, z = zoomRef.current
    if (!svg || !z) return
    const target = zoomIdentity.translate(t.x, t.y).scale(t.k)
    const from = transform
    if (typeof requestAnimationFrame !== 'function') { select(svg).call(z.transform, target); return }
    const t0 = performance.now()
    const step = (now: number) => {
      const u = Math.min(1, (now - t0) / 400)
      const e = u * (2 - u)
      select(svg).call(z.transform, zoomIdentity.translate(from.x + (target.x - from.x) * e, from.y + (target.y - from.y) * e).scale(from.k + (target.k - from.k) * e))
      if (u < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }

  useEffect(() => {
    const n = selected ? nodesRef.current.get(selected) : null
    if (!n || n.x == null || n.y == null) return
    const k = Math.max(transform.k, 1.2)
    moveTo({ k, x: W / 2 - k * n.x, y: H / 2 - k * n.y })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  const dim = (id: string) => (near && !near.has(id) ? 0.12 : 1)
  const hovered = hover ? nodesRef.current.get(hover.id) : null

  return (
    <div className="relative h-full w-full overflow-hidden bg-bg">
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="h-full w-full select-none">
        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
          {links.map((l, i) => {
            const s = l.source as SNode, t = l.target as SNode
            const conflict = l.edge.kind === 'conflict'
            const op = near ? (near.has(s.id) && near.has(t.id) ? 0.8 : 0.04) : conflict ? 0.9 : 0.18
            return (
              <g key={i}>
                <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke={conflict ? 'var(--color-conflict)' : 'var(--color-edge)'}
                  strokeWidth={conflict ? 1.5 : 0.6} strokeDasharray={conflict ? '5 4' : undefined} opacity={op} pointerEvents="none" />
                {conflict && (
                  <line data-edge-kind="conflict" x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="transparent" strokeWidth={10}
                    style={{ cursor: 'pointer' }} onClick={() => l.edge.pages?.[0] && onSelect(l.edge.pages[0])} />
                )}
              </g>
            )
          })}
          {vis.nodes.map(n => {
            const s = n as SNode, r = nodeRadius(n), fill = nodeColour(n, colourMode)
            const showLabel = (labels && r >= 10) || hover?.id === n.id || (labels && near?.has(n.id) === true)
            return (
              <g key={n.id} data-node-id={n.id} transform={`translate(${s.x},${s.y})`} opacity={dim(n.id)} style={{ cursor: 'pointer' }}
                onClick={() => onSelect(n.id)}
                onMouseEnter={e => setHover({ id: n.id, x: e.clientX, y: e.clientY })}
                onMouseMove={e => setHover({ id: n.id, x: e.clientX, y: e.clientY })}
                onMouseLeave={() => setHover(null)}>
                {n.kind === 'source'
                  ? <rect x={-r} y={-r} width={2 * r} height={2 * r} rx={2} fill={fill} />
                  : <circle r={r} fill={fill} />}
                {selected === n.id && <circle r={r + 4} fill="none" stroke="var(--color-text)" strokeWidth={1.5 / transform.k} />}
                {showLabel && <text y={r + 11} textAnchor="middle" fontSize={10} fill="var(--color-text)" pointerEvents="none">{n.title}</text>}
              </g>
            )
          })}
        </g>
      </svg>
      <Controls
        labels={labels} colourMode={colourMode}
        onReset={() => { setHidden(new Set()); moveTo(fitTarget()); onReset?.() }}
        onLabels={() => setLabels(v => !v)}
        onColour={() => setColourMode(m => (m === 'kind' ? 'cluster' : 'kind'))}
        onFind={q => { const f = findByTitle(vis.nodes, q); if (f) onSelect(f.id) }}
      />
      <Legend hidden={hidden} onToggle={k => setHidden(h => { const x = new Set(h); if (!x.delete(k)) x.add(k); return x })} />
      {hover && hovered && (
        <div className="pointer-events-none fixed z-10 rounded border border-border bg-surface px-2 py-1 text-xs" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          <div className="font-medium">{hovered.title}</div>
          <div className="text-muted">{hovered.kind}{hovered.confidence ? ` · ${hovered.confidence}` : ''}{hovered.kind !== 'source' ? ` · ${sources.get(hovered.id) ?? 0} sources` : ''}</div>
        </div>
      )}
    </div>
  )
}
