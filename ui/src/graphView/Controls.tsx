import { useState } from 'react'
import { Maximize2, Tag, Palette, Search } from 'lucide-react'
import type { Kind } from '../types'
import { KINDS } from './style'

const btn = 'flex items-center gap-1 rounded border border-border bg-surface/90 px-2 py-1 text-xs text-muted hover:text-text'

export function Legend({ hidden, onToggle }: { hidden: Set<Kind>; onToggle: (k: Kind) => void }) {
  return (
    <div className="absolute bottom-3 left-3 flex flex-col gap-1 rounded border border-border bg-surface/90 p-2 text-xs">
      {KINDS.map(k => (
        <button key={k} type="button" onClick={() => onToggle(k)} className={`flex items-center gap-2 ${hidden.has(k) ? 'opacity-40' : ''}`}>
          <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: `var(--color-kind-${k})` }} />
          <span>{k}</span>
        </button>
      ))}
    </div>
  )
}

export interface ControlsProps {
  labels: boolean
  colourMode: 'kind' | 'cluster'
  onReset: () => void
  onLabels: () => void
  onColour: () => void
  onFind: (q: string) => void
}

export function Controls(p: ControlsProps) {
  const [q, setQ] = useState('')
  return (
    <div className="absolute left-3 top-3 flex flex-wrap items-center gap-2">
      <button type="button" className={btn} onClick={p.onReset}><Maximize2 size={12} />Reset</button>
      <button type="button" className={btn} onClick={p.onLabels}><Tag size={12} />Labels {p.labels ? 'on' : 'off'}</button>
      <button type="button" className={btn} onClick={p.onColour}><Palette size={12} />Colour: {p.colourMode}</button>
      <label className={btn}>
        <Search size={12} />
        <input
          value={q}
          placeholder="Find…"
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') p.onFind(q) }}
          className="w-32 bg-transparent text-text outline-none"
        />
      </label>
    </div>
  )
}
