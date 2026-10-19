import { expect, test } from 'vitest'
import { pushTrail } from './trail'

test('pushTrail', () => {
  expect(pushTrail(['a'], 'a')).toEqual(['a'])
  expect(pushTrail(['a'], 'b')).toEqual(['a', 'b'])
  const t = pushTrail(Array.from({ length: 30 }, (_, i) => `${i}`), 'x')
  expect(t).toHaveLength(30)
  expect(t[0]).toBe('1')
})
