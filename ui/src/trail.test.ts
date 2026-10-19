import { expect, test } from 'vitest'
import { pushTrail } from './trail'

test('pushTrail', () => {
  expect(pushTrail(['a'], 'a')).toEqual(['a'])
  expect(pushTrail(['a'], 'b')).toEqual(['a', 'b'])
  const t = pushTrail(Array.from({ length: 30 }, (_, i) => `${i}`), 'x')
  expect(t).toHaveLength(30)
  expect(t[0]).toBe('1')
})

test('pushTrail replaces the last entry when both paths belong to the same node', () => {
  const o = new Map([['w/a.md', 'n1'], ['v/a.md', 'n1'], ['w/b.md', 'n2']])
  expect(pushTrail(['w/b.md', 'w/a.md'], 'v/a.md', o)).toEqual(['w/b.md', 'v/a.md'])
  expect(pushTrail(['w/a.md'], 'w/b.md', o)).toEqual(['w/a.md', 'w/b.md'])
})
