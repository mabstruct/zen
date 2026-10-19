export type Kind = 'topic' | 'entity' | 'synthesis' | 'source'
export type Confidence = 'low' | 'medium' | 'high' | null
export interface GNode {
  id: string
  title: string
  kind: Kind
  clusters: string[]
  confidence: Confidence
  conflicts: string[]
  updated: string | null
  wiki: string | null
  vault: string | null
  ingested: boolean
  inDegree: number
}
export interface GEdge {
  from: string
  to: string
  kind: 'cites' | 'links' | 'conflict'
  conflict?: string
  pages?: string[]
}
export interface Graph {
  generated: string
  nodes: GNode[]
  edges: GEdge[]
}
export interface MapNode {
  id: string
  path: string | null
  title: string
  type: string
  cluster: string | null
  updated: string | null
  confidence: Confidence
  conflicts: string[]
}
export interface ZenMap {
  generated: string
  nodes: MapNode[]
  edges: { from: string; to: string; kind: string }[]
}
