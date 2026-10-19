import { expect, test } from 'vitest'
import { parseHash, renderMarkdown, resolveHref, splitCompanion, toHash } from './markdown'

const O = new Map([['90_wiki/entities/vaswani.md', '90_wiki/entities/vaswani.md'],
  ['11_research/idea note.md', '11_research/idea note.md'], ['90_wiki/sources/attn.md', '10_ai/attn.md']])
const FROM = '90_wiki/topics/attention.md'
test('resolveHref', () => {
  expect(resolveHref(FROM, '../entities/vaswani.md#role', O)).toEqual({ type: 'node', id: '90_wiki/entities/vaswani.md', path: '90_wiki/entities/vaswani.md' })
  expect(resolveHref(FROM, '../../11_research/idea%20note.md', O)).toMatchObject({ type: 'node', id: '11_research/idea note.md' })
  expect(resolveHref(FROM, '<../../11_research/idea note.md>', O)).toMatchObject({ type: 'node', id: '11_research/idea note.md' })
  expect(resolveHref(FROM, '../sources/attn.md', O)).toEqual({ type: 'node', id: '10_ai/attn.md', path: '90_wiki/sources/attn.md' })
  expect(resolveHref(FROM, '../../10_ai/_originals/attn.pdf', O)).toEqual({ type: 'original' })
  expect(resolveHref(FROM, 'https://arxiv.org/abs/1706.03762', O)).toEqual({ type: 'external', href: 'https://arxiv.org/abs/1706.03762' })
  expect(resolveHref(FROM, '../topics/nowhere.md', O)).toEqual({ type: 'text' })
})
test('renderMarkdown is inert against raw HTML', () => {
  const html = renderMarkdown('x <script>window.__pwned=1</script> <img src=x onerror="window.__pwned=1">', FROM, O)
  expect(html).not.toMatch(/<script|onerror/i)
})
test('conflict callouts', () => {
  expect(renderMarkdown('> [!conflict] #c-0001 — open\n> A: a', FROM, O)).toContain('zen-conflict--open')
  expect(renderMarkdown('> [!conflict] #c-0002 — resolved\n> A: a', FROM, O)).toContain('zen-conflict--resolved')
})
test('hash round-trip with spaces and unicode', () => {
  for (const p of ['11_research/idea note.md', '90_wiki/entities/jürgen.md']) expect(parseHash(toHash(p)).path).toBe(p)
  expect(parseHash('#/').path).toBeNull()
  expect(parseHash('').path).toBeNull()
  expect(parseHash('#/p/%E0%A4%A').path).toBeNull()
  expect(toHash('11_research/idea note.md')).toBe('#/p/11_research/idea%20note.md')
})
test('splitCompanion', () => {
  expect(splitCompanion('---\nt: 1\n---\n## Summary\nS\n\n## Extracted text\nE')).toEqual({ summary: '## Summary\nS\n', extracted: 'E' })
})
test('link rendering', () => {
  const md = '[V](../entities/vaswani.md) [A](https://x.org/a) [P](../../10_ai/_originals/a.pdf) [D](../topics/none.md) [S](../sources/attn.md)'
  const html = renderMarkdown(md, FROM, O)
  expect(html).toContain('href="#/p/90_wiki/entities/vaswani.md"')
  expect(html).toContain('data-zen-path="90_wiki/entities/vaswani.md"')
  expect(html).toContain('href="#/p/90_wiki/sources/attn.md"')
  expect(html).toMatch(/href="https:\/\/x\.org\/a"[^>]*target="_blank"/)
  expect(html).toContain('rel="noopener noreferrer"')
  expect(html).toContain('<span class="zen-original">P (original not included)</span>')
  expect(html).toContain('<span class="zen-deadlink">D</span>')
})
