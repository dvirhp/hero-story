import { test, expect } from '@playwright/test';

test('local frontend responds', async ({ page }) => {
  test.skip(!process.env.STORYFORGE_E2E_URL, 'Frontend is absent from the QA baseline');
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) await route.continue();
    else await route.abort();
  });
  const response = await page.goto('/');
  expect(response?.ok()).toBeTruthy();
  await expect(page.locator('body')).not.toBeEmpty();
});
