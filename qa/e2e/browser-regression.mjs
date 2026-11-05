// Real Chromium against a committed frontend snapshot. App service remains mocked.
// No backend integration, persistence, semantic quality or full a11y claim.
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const modulePath = process.env.STORYFORGE_PLAYWRIGHT_MODULE;
if (!modulePath) throw new Error('Set STORYFORGE_PLAYWRIGHT_MODULE to an installed playwright/index.mjs');
const { chromium } = await import(pathToFileURL(modulePath));
const baseURL = process.env.STORYFORGE_E2E_URL ?? 'http://127.0.0.1:4184';
assert(['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname));
const browser = await chromium.launch({ headless: true,
  ...(process.env.STORYFORGE_CHROMIUM ? { executablePath: process.env.STORYFORGE_CHROMIUM } : {}) });
const results = [];

async function check(name, action) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' });
  const page = await context.newPage();
  page.setDefaultTimeout(5000);
  const errors = [], external = [], api = [];
  page.on('pageerror', () => errors.push('browser exception'));
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(baseURL).origin) {
      external.push(url.origin); await route.abort();
    } else {
      if (/\/v[123]\//.test(url.pathname)) api.push(url.pathname);
      await route.continue();
    }
  });
  try {
    await page.goto(baseURL);
    await page.getByRole('heading', { name: 'Small name. Big adventure.' }).waitFor();
    await action(page);
    assert.equal(errors.length, 0, 'browser exceptions');
    assert.equal(external.length, 0, 'external requests attempted');
    assert.equal(api.length, 0, 'demo unexpectedly contacted an API');
    results.push({ name, status: 'passed', level: 'browser with mock service' });
  } catch (error) {
    results.push({ name, status: 'failed', errorType: error.name });
    console.error(`FAIL ${name}: ${error.message.slice(0, 500)}`);
  } finally { await context.close(); }
}

async function form(page, { name = 'Zoë', language = 'en', pages = 3 } = {}) {
  await page.getByRole('button', { name: 'Create a story' }).first().click();
  await page.getByLabel('Child’s name').fill(name);
  await page.getByLabel('What is the story about?').fill('A moonlit garden 🌙');
  await page.getByLabel('Age', { exact: true }).fill('0');
  await page.getByLabel('Age unit').selectOption('months');
  await page.getByLabel('Number of pages').fill(String(pages));
  await page.getByLabel('Story language', { exact: true }).selectOption(language);
}
async function generate(page) {
  await page.getByRole('button', { name: 'Make our story' }).click();
  await page.getByRole('heading', { name: 'A world is taking shape…' }).waitFor();
  await page.locator('article').waitFor();
}

try {
  await check('responsive landing widths and keyboard skip link', async page => {
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    // App initially focuses main-content; focus the skip link to verify its
    // keyboard activation without assuming the browser's initial tab position.
    await page.getByRole('link', { name: 'Skip to content' }).focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'main-content');
  });
  await check('age change preserves pages and reader boundaries', async page => {
    await form(page);
    await page.getByLabel('Age', { exact: true }).fill('120');
    assert.equal(await page.getByLabel('Number of pages').inputValue(), '3');
    await generate(page);
    assert((await page.locator('article').innerText()).includes('Zoë'));
    assert(await page.getByRole('button', { name: 'Previous page' }).isDisabled());
    await page.getByRole('button', { name: 'Next page' }).click();
    await page.getByRole('button', { name: 'Next page' }).click();
    assert(await page.getByRole('button', { name: 'Next page' }).isDisabled());
    assert((await page.locator('.page-counter').innerText()).includes('3 of 3'));
  });
  await check('Hebrew logical Unicode and mixed UI direction on mobile', async page => {
    await page.setViewportSize({ width: 390, height: 844 });
    await form(page, { name: 'אוֹר לי', language: 'he', pages: 2 });
    await generate(page);
    assert.equal(await page.locator('html').getAttribute('dir'), 'ltr');
    assert.equal(await page.locator('article').getAttribute('dir'), 'rtl');
    assert.equal(await page.locator('article').getAttribute('lang'), 'he');
    assert((await page.locator('article').innerText()).includes('אוֹר לי'));
    await page.getByLabel('Interface language').selectOption('he');
    assert.equal(await page.locator('html').getAttribute('dir'), 'rtl');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  });
  await check('invalid form announces error and focuses field', async page => {
    await page.getByRole('button', { name: 'Create a story' }).first().click();
    await page.getByRole('button', { name: 'Make our story' }).click();
    await page.locator('[role=alert]').waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('aria-invalid') === 'true');
    assert.equal(await page.locator('article').count(), 0);
  });
  await check('cancel prevents stale reader and retains brief', async page => {
    await form(page);
    await page.getByRole('button', { name: 'Make our story' }).click();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    assert.equal(await page.getByLabel('Child’s name').inputValue(), 'Zoë');
    await page.waitForTimeout(2000); // Beyond the mock service's 1800 ms delay.
    assert.equal(await page.locator('article').count(), 0);
  });
  await check('untrusted HTML-like name renders as text', async page => {
    const name = '<img src=x onerror=alert(1)>';
    await form(page, { name });
    await generate(page);
    assert((await page.locator('article').innerText()).includes(name));
    assert.equal(await page.locator('article img').count(), 0);
  });
  await check('refresh discards unsaved brief without storage', async page => {
    await form(page);
    await page.reload();
    await page.getByRole('heading', { name: 'Small name. Big adventure.' }).waitFor();
    await page.getByRole('button', { name: 'Create a story' }).first().click();
    assert.equal(await page.getByLabel('Child’s name').inputValue(), '');
    assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  });
  await check('demo error and empty reader recovery', async page => {
    await page.locator('summary').filter({ hasText: 'Demo states' }).click();
    await page.getByRole('button', { name: 'Preview error', exact: true }).click();
    await page.getByRole('heading', { name: 'This story needs another moment.' }).waitFor();
    await page.getByRole('button', { name: 'Return to my brief' }).click();
    await page.getByLabel('Child’s name').waitFor();
    await page.getByRole('button', { name: 'Preview empty reader', exact: true }).click();
    await page.getByRole('heading', { name: 'Your next adventure is waiting.' }).waitFor();
    assert.equal(await page.locator('article').count(), 0);
  });
  console.log(JSON.stringify({ results, passed: results.filter(r => r.status === 'passed').length,
    failed: results.filter(r => r.status === 'failed').length }, null, 2));
  if (results.some(r => r.status === 'failed')) process.exitCode = 1;
} finally { await browser.close(); }
