import { expect, test } from '@playwright/test'

test('browse along links', async ({ page }) => {
  await page.goto('./#/')
  await page.locator('[data-node-id="90_wiki/topics/attention.md"]').click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Attention')
  await page.locator('a[data-zen-path="90_wiki/sources/attn.md"]').first().click()
  await expect(page).toHaveURL(/#\/p\/90_wiki\/sources\/attn\.md$/)
  await expect(page.getByTestId('trail')).toContainText('Attention')
  await page.getByRole('tab', { name: 'Text' }).click()
  await page.locator('details').click()
  expect(await page.evaluate(() => (window as any).__pwned)).toBeUndefined()
  await page.goto('./#/p/nope.md')
  await expect(page.getByText(/Not in this snapshot/)).toBeVisible()
})
