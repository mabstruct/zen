import { useEffect, useMemo, useState } from 'react'
import type { MouseEvent, ReactNode } from 'react'
import { getPage } from '../data'
import { renderMarkdown, splitCompanion, stripFrontmatter } from '../markdown'
import type { Graph } from '../types'

const DOTS = { low: 1, medium: 2, high: 3 } as const

function Dots({ level }: { level: 'low' | 'medium' | 'high' | null }) {
  const n = level ? DOTS[level] : 0
  return (
    <span aria-label={`confidence: ${level ?? 'none'}`} title={`confidence: ${level ?? 'none'}`} className="inline-flex gap-0.5">
      {[0, 1, 2].map(i => (
        <span key={i} className={`inline-block h-2 w-2 rounded-full ${i < n ? 'bg-accent' : 'bg-border'}`} />
      ))}
    </span>
  )
}

const demote = (html: string) => html.replace(/<(\/?)h1(?=[\s>])/g, '<$1h2')

export function Reader({ graph, owners, path, onNavigate }: {
  graph: Graph
  owners: Map<string, string>
  path: string
  onNavigate: (path: string) => void
}) {
  const nodeId = owners.get(path)
  const node = useMemo(() => (nodeId === undefined ? null : graph.nodes.find(n => n.id === nodeId) ?? null), [graph, nodeId])
  const [text, setText] = useState<{ path: string; md: string | null } | null>(null)

  useEffect(() => {
    if (!node) return
    let live = true
    getPage(path).then(md => { if (live) setText({ path, md }) }, () => { if (live) setText({ path, md: null }) })
    return () => { live = false }
  }, [node, path])

  if (!node) return <div className="p-4 text-muted">Not in this snapshot: {path}</div>

  const isCompanion = node.kind === 'source' && (path === node.vault || node.wiki === null)
  const loaded = text && text.path === path ? text : null
  let body: ReactNode = null
  if (loaded) {
    if (loaded.md === null) {
      body = <p className="text-muted">Page not available: {path}</p>
    } else if (isCompanion) {
      const { summary, extracted } = splitCompanion(loaded.md)
      body = (
        <>
          <div className="zen-prose" dangerouslySetInnerHTML={{ __html: demote(renderMarkdown(summary, path, owners)) }} />
          {extracted !== null && (
            <details className="mt-4">
              <summary className="cursor-pointer text-muted">Extracted text</summary>
              <div className="zen-prose" dangerouslySetInnerHTML={{ __html: demote(renderMarkdown(extracted, path, owners)) }} />
            </details>
          )}
        </>
      )
    } else {
      body = <div className="zen-prose" dangerouslySetInnerHTML={{ __html: demote(renderMarkdown(stripFrontmatter(loaded.md), path, owners)) }} />
    }
  }

  const click = (e: MouseEvent<HTMLElement>) => {
    const a = (e.target as HTMLElement).closest('a[data-zen-path]')
    if (!a) return
    e.preventDefault()
    onNavigate(a.getAttribute('data-zen-path')!)
  }

  const hasTabs = node.kind === 'source'
  const tab = (label: string, target: string | null, active: boolean) => (
    <button
      role="tab"
      aria-selected={active}
      disabled={target === null}
      onClick={() => { if (!active && target) onNavigate(target) }}
      className={`px-3 py-1 text-sm ${active ? 'border-b-2 border-accent text-text' : 'text-muted'}`}
    >
      {label}
    </button>
  )

  return (
    <article onClick={click} className="p-4">
      <header className="mb-3">
        <h1 className="text-xl font-semibold">{node.title}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          <span>{node.kind}</span>
          <Dots level={node.confidence} />
          {node.clusters.length > 0 && <span>{node.clusters.join(', ')}</span>}
          {node.updated && <span>updated {node.updated.slice(0, 10)}</span>}
          {node.conflicts.length > 0 && <span className="text-conflict">open conflicts: {node.conflicts.join(', ')}</span>}
        </div>
      </header>
      {hasTabs && (
        <div role="tablist" className="mb-3 flex border-b border-border">
          {tab('Wiki summary', node.wiki, !isCompanion)}
          {tab('Text', node.vault, isCompanion)}
        </div>
      )}
      {body}
    </article>
  )
}
