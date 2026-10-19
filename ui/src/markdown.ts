import { Marked, type Tokens } from 'marked'
import DOMPurify from 'isomorphic-dompurify'
import { resolvePath } from './graph'

export type LinkTarget =
  | { type: 'node'; id: string; path: string }
  | { type: 'original' }
  | { type: 'external'; href: string }
  | { type: 'text' }

export function resolveHref(from: string, href: string, owners: Map<string, string>): LinkTarget {
  const raw = href.trim()
  if (/^https?:/i.test(raw)) return { type: 'external', href: raw }
  const path = resolvePath(from, raw)
  if (path.includes('/_originals/') || path.startsWith('_originals/')) return { type: 'original' }
  const id = owners.get(path)
  if (id !== undefined) return { type: 'node', id, path }
  return { type: 'text' }
}

export function stripFrontmatter(md: string): string {
  const m = /^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/.exec(md)
  return m ? md.slice(m[0].length) : md
}

export function splitCompanion(md: string): { summary: string; extracted: string | null } {
  const body = stripFrontmatter(md)
  const m = /^## Extracted text[ \t]*\r?\n?/m.exec(body)
  if (!m) return { summary: body, extracted: null }
  return { summary: body.slice(0, m.index).trimEnd() + '\n', extracted: body.slice(m.index + m[0].length) }
}

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

const CONFLICT = /^\s*\[!conflict\]\s+(#c-\d+)\s+—\s+(open|resolved)/

export function toHash(path: string): string {
  return '#/p/' + path.split('/').map(encodeURIComponent).join('/')
}

export function parseHash(hash: string): { path: string | null } {
  if (!hash.startsWith('#/p/')) return { path: null }
  try {
    const path = hash.slice(4).split('/').map(decodeURIComponent).join('/')
    return { path: path || null }
  } catch {
    return { path: null }
  }
}

const ALLOWED_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'em', 'strong', 'del', 'a', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'br', 'details', 'summary']
const ALLOWED_ATTR = ['href', 'class', 'data-zen-path', 'data-zen-link', 'target', 'rel', 'align', 'start']

export function renderMarkdown(md: string, from: string, owners: Map<string, string>): string {
  const nonce = Math.random().toString(36).slice(2)
  const marked = new Marked()
  marked.use({
    renderer: {
      link(token: Tokens.Link) {
        const target = resolveHref(from, token.href, owners)
        const inner = this.parser.parseInline(token.tokens)
        switch (target.type) {
          case 'external':
            return `<a data-zen-link="${nonce}" href="${esc(target.href)}" target="_blank" rel="noopener noreferrer">${inner}</a>`
          case 'node':
            return `<a data-zen-link="${nonce}" href="${esc(toHash(target.path))}" data-zen-path="${esc(target.path)}">${inner}</a>`
          case 'original':
            return `<span class="zen-original">${inner} (original not included)</span>`
          default:
            return `<span class="zen-deadlink">${inner}</span>`
        }
      },
      image(token: Tokens.Image) {
        const target = resolveHref(from, token.href, owners)
        const alt = esc(token.text)
        return target.type === 'original'
          ? `<span class="zen-original">${alt} (original not included)</span>`
          : `<span class="zen-deadlink">${alt}</span>`
      },
      blockquote(token: Tokens.Blockquote) {
        const inner = this.parser.parse(token.tokens)
        const m = CONFLICT.exec(token.text)
        const cls = m ? ` class="zen-conflict zen-conflict--${m[2]}"` : ''
        return `<blockquote${cls}>\n${inner}</blockquote>\n`
      },
    },
  })
  const html = marked.parse(md, { async: false }) as string
  const hook = (node: Element) => {
    if (node.nodeName !== 'A') return
    if (node.getAttribute('data-zen-link') === nonce) {
      node.removeAttribute('data-zen-link')
      return
    }
    const span = node.ownerDocument.createElement('span')
    span.className = 'zen-deadlink'
    span.textContent = node.textContent
    node.replaceWith(span)
  }
  DOMPurify.addHook('afterSanitizeAttributes', hook)
  try {
    return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR })
  } finally {
    DOMPurify.removeHook('afterSanitizeAttributes', hook)
  }
}
