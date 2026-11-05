// Independent browser QA of captured bd40358. Real browser; local mock data only.
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const snapshot = path.resolve(process.env.STORYFORGE_UX_SNAPSHOT ?? 'qa/.local/frontend-ux-current/frontend');
const moduleURL = name => pathToFileURL(path.join(snapshot, 'node_modules', name)).href;
const { chromium } = await import(moduleURL('playwright/index.mjs'));
const { default: AxeBuilder } = await import(moduleURL('@axe-core/playwright/dist/index.mjs'));
const origin = process.env.STORYFORGE_UX_URL ?? 'http://127.0.0.1:4194';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const screenshots = path.resolve('docs/qa-screenshots/frontend-ux');
await fs.mkdir(screenshots, { recursive: true });
const browser = await chromium.launch({ headless: true,
  executablePath: process.env.STORYFORGE_CHROMIUM ?? 'C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe' });
const results = [], findings = [], a11y = [], metrics = [];

async function check(name, action, options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 },
    serviceWorkers: 'block', ...options });
  const page = await context.newPage();
  page.setDefaultTimeout(6000);
  const errors = [], forbidden = [];
  page.on('pageerror', () => errors.push('browser exception'));
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(origin).origin || /^\/v[123]\//.test(url.pathname)) {
      forbidden.push(url.pathname); await route.abort();
    } else await route.continue();
  });
  try {
    await action(page, context);
    assert.deepEqual(errors, []);
    assert.deepEqual(forbidden, []);
    results.push({ name, status: name.startsWith('UX-') ? 'defect reproduced' : 'passed', evidence: 'real Chromium, local mock app' });
  } catch (error) {
    results.push({ name, status: 'failed', error: error.message.slice(0, 450) });
    console.error(`FAIL ${name}: ${error.message.slice(0, 450)}`);
  } finally { await context.close(); }
}
const goto = (page, route = '/') => page.goto(`${origin}/#${route}`);
const shot = (page, name) => page.screenshot({ path: path.join(screenshots, name + '.png'), fullPage: true, animations: 'disabled' });
const open = page => page.getByRole('button', { name: /Open the book|פתיחת הספר/ }).first().click();
const overflow = page => page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
async function audit(page, scenario) {
  const report = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
  a11y.push({ scenario, violations: report.violations.map(v => ({ id: v.id, impact: v.impact,
    wcag: v.tags.filter(t => t.startsWith('wcag')), nodes: v.nodes.map(n => n.target) })) });
  assert.equal(report.violations.length, 0, `axe violations in ${scenario}`);
}

try {
  for (const language of ['en', 'he']) {
    await check(`reader physical coordinates, order and backwards keys ${language}`, async page => {
      await goto(page, `/read/sample-moon-fox-${language}`);
      const rtl = language === 'he';
      assert.equal(await page.locator('.cover-on-table').getAttribute('data-hinge'), rtl ? 'right' : 'left');
      await open(page);
      const first = await page.locator('[data-page-number="1"]').boundingBox();
      const blank = await page.locator('.inside-cover').first().boundingBox();
      assert(rtl ? first.x < blank.x : first.x > blank.x);
      const seen = [1];
      while (!(await page.getByRole('button', { name: 'Next page', exact: false }).isDisabled())) {
        await page.keyboard.press(rtl ? 'ArrowLeft' : 'ArrowRight');
        const visible = await page.locator('[data-page-number]').evaluateAll(elements =>
          elements.map(el => ({ n: Number(el.getAttribute('data-page-number')), x: el.getBoundingClientRect().x })));
        seen.push(...visible.map(v => v.n));
        if (visible.length === 2) assert(rtl ? visible[0].x > visible[1].x : visible[0].x < visible[1].x);
      }
      assert.deepEqual(seen, [1, 2, 3, 4, 5, 6]);
      await page.keyboard.press(rtl ? 'ArrowRight' : 'ArrowLeft');
      assert.deepEqual(await page.locator('[data-page-number]').evaluateAll(es => es.map(e => Number(e.dataset.pageNumber))), [4, 5]);
      await shot(page, `reader-${language}-desktop`);
    });
    await check(`native touch single-page direction ${language}`, async (page, context) => {
      await goto(page, `/read/sample-moon-fox-${language}`);
      await open(page);
      assert.equal(await page.locator('[data-page-number]').count(), 1);
      await page.locator('.physical-book').scrollIntoViewIfNeeded();
      const box = await page.locator('.physical-book').boundingBox();
      const start = language === 'he' ? 90 : 280, end = language === 'he' ? 280 : 90;
      const y = Math.max(80, Math.min(500, box.y + 100));
      const session = await context.newCDPSession(page);
      await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: start, y }] });
      await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: end, y }] });
      await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      await page.locator('[data-page-number="2"]').waitFor();
      assert(!(await overflow(page)));
      await shot(page, `reader-${language}-mobile`);
    }, { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  }
  await check('reader reduced motion and actual fullscreen enter/exit', async page => {
    await goto(page, '/read/sample-moon-fox-he');
    assert.equal(await page.locator('.cover-on-table .book-cover').evaluate(el => getComputedStyle(el).transform), 'none');
    await open(page);
    assert.equal(await page.locator('.physical-spread').evaluate(el => getComputedStyle(el).animationName), 'none');
    await page.getByRole('button', { name: 'Read fullscreen', exact: true }).click();
    await page.waitForFunction(() => !!document.fullscreenElement);
    assert(await page.evaluate(() => !!document.fullscreenElement));
    await page.getByRole('button', { name: 'Leave fullscreen', exact: true }).click();
    await page.waitForFunction(() => !document.fullscreenElement);
    assert.equal(await page.evaluate(() => !!document.fullscreenElement), false);
  }, { reducedMotion: 'reduce' });
  await check('physical reader direction remains book-owned in opposite interface locales', async page => {
    for (const language of ['en', 'he']) {
      await goto(page, `/read/sample-moon-fox-${language}`);
      const ui = language === 'he' ? 'en' : 'he';
      await page.locator('#ui-language').selectOption(ui);
      await page.waitForFunction(lang => document.documentElement.lang === lang, ui);
      await open(page);
      await page.keyboard.press(language === 'he' ? 'ArrowLeft' : 'ArrowRight');
      const boxes = await page.locator('[data-page-number]').evaluateAll(es => es.map(e => ({
        n: Number(e.dataset.pageNumber), x: e.getBoundingClientRect().x })));
      assert.deepEqual(boxes.map(b => b.n), [2, 3]);
      assert(language === 'he' ? boxes[0].x > boxes[1].x : boxes[0].x < boxes[1].x);
      assert.equal(await page.locator('.physical-book').getAttribute('dir'), language === 'he' ? 'rtl' : 'ltr');
    }
  });

  for (const width of [360, 390, 768, 1024, 1440]) {
    await check(`responsive routes and reader scaling at ${width}`, async page => {
      for (const route of ['/', '/books', '/books/sky-whale', '/personalize/sky-whale', '/my-books', '/studio/demo-draft', '/read/sample-moon-fox-he']) {
        await goto(page, route);
        await page.locator('main').waitFor();
        assert(!(await overflow(page)), `${route} overflows at ${width}`);
      }
      await open(page);
      const folios = await page.locator('[data-page-number]').count();
      assert.equal(folios, 1);
      await page.keyboard.press('ArrowLeft');
      assert.equal(await page.locator('[data-page-number]').count(), width >= 900 ? 2 : 1);
      assert(!(await overflow(page)));
      const bounds = await page.locator('.physical-spread').boundingBox();
      assert(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
      metrics.push({ width, routes: 7, horizontalOverflow: false });
    }, { viewport: { width, height: 900 } });
  }
  await check('keyboard navigation, mobile menu Escape, and all three creation links', async page => {
    await goto(page);
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
    await page.keyboard.press('Enter');
    assert.equal(await page.locator(':focus').getAttribute('id'), 'main-content');
    for (const route of ['/create/ai', '/books', '/studio/new']) {
      await goto(page, route);
      assert.equal(await page.locator('main').count(), 1);
    }
    await page.setViewportSize({ width: 360, height: 800 });
    await page.getByRole('button', { name: 'Menu', exact: true }).click();
    await page.keyboard.press('Escape');
    assert(await page.getByRole('button', { name: 'Menu', exact: true }).evaluate(el => el === document.activeElement));
  });
  await check('schema-specific personalization fields, artwork, color and language', async page => {
    await goto(page, '/personalize/small-hero');
    assert.equal(await page.locator('#personal-companion').count(), 0);
    await page.locator('#personal-name').fill('Zoë');
    await page.locator('#personal-outfit').selectOption('striped');
    assert((await page.locator('.personal-preview .book-cover img').getAttribute('src')).endsWith('hero-striped.svg'));
    assert.equal(await page.locator('#personal-color').count(), 0); // Not supported by this template.
    await goto(page, '/personalize/sky-whale');
    await page.locator('#personal-color').selectOption('#c9c0e0');
    assert.equal(await page.locator('.personal-preview .book-cover').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(201, 192, 224)');
    await page.locator('#template-language').selectOption('he');
    assert.equal(await page.locator('.personal-preview .book-cover').getAttribute('dir'), 'rtl');
    await goto(page, '/personalize/moon-fox');
    assert.equal(await page.locator('#personal-outfit').count(), 0);
    assert.equal(await page.locator('#personal-companion').count(), 0);
  });
  await check('template required validation, preview and saved-book text consistency', async page => {
    await goto(page, '/personalize/sky-whale');
    await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
    await page.locator('[role=alert]').waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('aria-invalid') === 'true');
    await page.locator('#personal-name').fill('אוֹר Lee');
    await page.locator('#personal-dedication').fill('For the moon and stars 🌙');
    await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
    const preview = await page.locator('.personal-preview .spread-words p').innerText();
    await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
    await open(page);
    assert.equal(await page.locator('.folio-page .spread-words p').innerText(), preview);
    await page.getByRole('link', { name: 'Back to my books' }).click();
    assert((await page.locator('.library-card').first().innerText()).includes('אוֹר Lee'));
  });
  await check('manual explicit save/reopen and stable page order', async page => {
    await goto(page, '/studio/new');
    await page.getByLabel('Book title').fill('QA ordered pages');
    await page.locator('#page-text').fill('First page');
    await page.getByRole('button', { name: /Add a page/ }).click();
    await page.locator('#page-text').fill('Second page');
    await page.getByRole('button', { name: 'Move earlier' }).click();
    await page.getByRole('button', { name: 'Save draft in this tab', exact: true }).click();
    await page.getByRole('link', { name: 'My books', exact: true }).last().click();
    await page.locator('.library-card').filter({ hasText: 'QA ordered pages' }).getByRole('link', { name: /Continue editing/ }).click();
    assert.equal(await page.locator('#page-text').inputValue(), 'Second page');
    assert.equal(await page.locator('.page-rail li').count(), 2);
  });

  // Characterization probes below reproduce defects, not successful acceptance checks.
  await check('UX-01: Hebrew cover spine remains physically on the left', async page => {
    await goto(page, '/read/sample-moon-fox-he');
    const cover = await page.locator('.cover-on-table .book-cover').boundingBox();
    const spine = await page.locator('.cover-on-table .book-spine').boundingBox();
    assert(spine.x < cover.x + cover.width / 2);
    findings.push({ id: 'UX-01', reproduced: true, scope: 'Hebrew cover spine; declared hinge is right' });
    await shot(page, 'UX-01-hebrew-cover-left-spine');
  });
  await check('UX-02: reader tool labels lag behind interface language', async page => {
    await goto(page, '/read/sample-moon-fox-en');
    await page.locator('#ui-language').selectOption('he');
    await page.waitForFunction(() => document.documentElement.lang === 'he');
    assert.equal(await page.getByRole('button', { name: 'Page overview', exact: true }).count(), 1);
    assert.equal(await page.getByRole('button', { name: 'מפת עמודים', exact: true }).count(), 0);
    findings.push({ id: 'UX-02', reproduced: true, scope: 'reader experience labels read stale document.lang during render' });
    await shot(page, 'UX-02-hebrew-ui-english-reader-tools');
  });
  await check('UX-03: user dedication is evaluated as a template', async page => {
    await goto(page, '/personalize/sky-whale');
    await page.locator('#personal-name').fill('Maya');
    await page.locator('#personal-dedication').fill('Dear {{name}}, from {{companion}}.');
    await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
    assert.equal(await page.locator('.personal-preview .spread-words p').innerText(), 'Dear Maya, from fox.');
    await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
    await open(page);
    assert.equal(await page.locator('.folio-page .spread-words p').innerText(), 'Dear Maya, from fox.');
    findings.push({ id: 'UX-03', reproduced: true, scope: 'dedication literal text changed in preview and saved snapshot' });
    await shot(page, 'UX-03-literal-dedication-changed');
  });
  await check('UX-04: preview roundtrip clears unsaved reload warning', async page => {
    await goto(page, '/studio/new');
    await page.getByLabel('Book title').fill('QA unsaved draft');
    await page.locator('#page-text').fill('A private synthetic draft');
    const prevented = () => page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented; });
    assert.equal(await prevented(), true);
    await page.getByRole('button', { name: 'Preview book', exact: true }).click();
    await page.getByRole('link', { name: 'Continue editing', exact: true }).click();
    assert.equal(await page.locator('#page-text').inputValue(), 'A private synthetic draft');
    assert.equal(await prevented(), false);
    findings.push({ id: 'UX-04', reproduced: true, scope: 'editor dirty state reset on unmount/remount' });
    await shot(page, 'UX-04-unsaved-preview-roundtrip');
  });
  await check('UX-05: companion selection has no inspectable preview page', async page => {
    await goto(page, '/personalize/sky-whale');
    await page.locator('#personal-name').fill('Maya');
    await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
    const before = await page.locator('.personal-preview').innerText();
    await page.locator('#personal-companion').selectOption('rabbit');
    assert.equal(await page.locator('.personal-preview').innerText(), before);
    assert.equal(await page.locator('.personal-preview select').count(), 0);
    findings.push({ id: 'UX-05', reproduced: true, scope: 'preview only exposes first page; companion occurs on second' });
    await shot(page, 'UX-05-companion-preview-no-feedback');
  });
  await check('UX-06: title overlaps dark illustration with insufficient contrast', async page => {
    await goto(page, '/read/sample-moon-fox-en');
    const geometry = await page.locator('.cover-on-table .book-cover').evaluate(cover => {
      const title = cover.querySelector('.cover-heading strong'), image = cover.querySelector('img');
      const a = title.getBoundingClientRect(), b = image.getBoundingClientRect();
      return { overlap: a.bottom - b.top, color: getComputedStyle(title).color,
        fontSize: getComputedStyle(title).fontSize };
    });
    assert(geometry.overlap > 0);
    assert.equal(geometry.color, 'rgb(37, 60, 66)');
    // moon.svg paints its top region with #414271, below the second title line.
    const luminance = hex => {
      const c = hex.match(/../g).map(v => parseInt(v, 16) / 255)
        .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
      return .2126 * c[0] + .7152 * c[1] + .0722 * c[2];
    };
    const a = luminance('253c42'), b = luminance('414271');
    const contrast = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    assert(contrast < 3); // Fails even the large, bold text threshold.
    findings.push({ id: 'UX-06', reproduced: true, contrast, geometry,
      scope: 'visual/SVG-background contrast; body title remains available outside cover' });
    await shot(page, 'UX-06-cover-title-contrast');
  });

  for (const language of ['en', 'he']) {
    await check(`axe WCAG A/AA including 2.2 tags and localization sweep ${language}`, async page => {
      for (const route of ['/', '/books', '/books/sky-whale', '/personalize/small-hero', '/my-books', '/studio/demo-draft', '/read/sample-moon-fox-he', '/generation-error']) {
        await goto(page, route);
        await page.locator('#ui-language').selectOption(language);
        await page.waitForFunction(lang => document.documentElement.lang === lang, language);
        if (route.startsWith('/read')) await open(page);
        await audit(page, `${language}:${route}`);
      }
    });
  }
} finally {
  await browser.close();
  const report = { snapshot: 'bd40358aa88c090d012dc0a47c067d5b3bd616de', results, findings, a11y, metrics,
    passed: results.filter(r => r.status === 'passed').length,
    reproducedDefects: results.filter(r => r.status === 'defect reproduced').length,
    failed: results.filter(r => r.status === 'failed').length };
  await fs.mkdir(path.resolve('qa/artifacts'), { recursive: true });
  await fs.writeFile(path.resolve('qa/artifacts/frontend-ux-results.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (report.failed) process.exitCode = 1;
}
