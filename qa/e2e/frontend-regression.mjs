// Independent QA regression for the committed Agent 2 frontend pin b09f54b.
// Real Chromium against the local demo build only. No API, provider, payment or
// external request is permitted. Findings are reported as present/resolved/
// unverified instead of treating old-defect characterization as acceptance.
//
// Environment:
//   STORYFORGE_UX_SNAPSHOT  frontend dir containing node_modules (default latest pin)
//   STORYFORGE_UX_URL       local preview origin (default http://127.0.0.1:4195)
//   STORYFORGE_UX_PIN       commit id written into the report
//   STORYFORGE_UX_SCREENSHOTS / STORYFORGE_UX_RESULTS  output paths
//   STORYFORGE_CHROMIUM     Chromium executable path

import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const snapshot = path.resolve(
  process.env.STORYFORGE_UX_SNAPSHOT ?? 'qa/.local/frontend-ux-latest/frontend',
);
const moduleURL = (name) =>
  pathToFileURL(path.join(snapshot, 'node_modules', name)).href;
const { chromium } = await import(moduleURL('playwright/index.mjs'));
const { default: AxeBuilder } = await import(
  moduleURL('@axe-core/playwright/dist/index.mjs')
);

const pin =
  process.env.STORYFORGE_UX_PIN ?? 'b09f54bc3ba0f6b175b71a80b7a3965b8d23429d';
const origin = process.env.STORYFORGE_UX_URL ?? 'http://127.0.0.1:4195';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const screenshots = path.resolve(
  process.env.STORYFORGE_UX_SCREENSHOTS ??
    'docs/qa-screenshots/frontend-ux-latest',
);
const resultsFile = path.resolve(
  process.env.STORYFORGE_UX_RESULTS ??
    'qa/artifacts/frontend-ux-latest-results.json',
);
await fs.mkdir(screenshots, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath:
    process.env.STORYFORGE_CHROMIUM ??
    'C:/Users/dvir3/AppData/Local/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-win64/chrome-headless-shell.exe',
});
const browserVersion = browser.version();

const results = [];
const findings = [];
const a11y = [];
const metrics = [];
const externalAttempts = [];

async function guardedPage(options = {}) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    serviceWorkers: 'block',
    ...options,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(8000);
  const errors = [];
  const forbidden = [];
  page.on('pageerror', (error) => errors.push(error.message.slice(0, 300)));
  await context.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(origin).origin || /^\/v[123]\//.test(url.pathname)) {
      forbidden.push(url.href);
      externalAttempts.push(url.href);
      await route.abort();
    } else {
      await route.continue();
    }
  });
  return { context, page, errors, forbidden };
}

async function check(name, action, options = {}) {
  const { context, page, errors, forbidden } = await guardedPage(options);
  try {
    await action(page, context);
    assert.deepEqual(errors, [], `browser exception: ${errors.join(' | ')}`);
    assert.deepEqual(forbidden, [], `blocked external request: ${forbidden.join(', ')}`);
    results.push({ name, status: name.startsWith('axe sweep') ? 'inspected' : 'passed', evidence: 'real Chromium, local demo build' });
    console.log(`${name.startsWith('axe sweep') ? 'INSPECTED' : 'PASS'} ${name}`);
  } catch (error) {
    results.push({ name, status: 'failed', error: error.message.slice(0, 600) });
    console.error(`FAIL ${name}: ${error.message.slice(0, 600)}`);
  } finally {
    await context.close();
  }
}

async function probe(definition, action) {
  const { context, page, errors, forbidden } = await guardedPage();
  try {
    const observed = await action(page, context);
    findings.push({
      id: definition.id,
      title: definition.title,
      severity: definition.severity,
      status: observed.status,
      expected: definition.expected,
      actual: observed.actual,
      evidence: observed.evidence,
    });
    results.push({
      name: `${definition.id} probe`,
      status: 'inspected',
      evidence: observed.status,
    });
    console.log(`PROBE ${definition.id}: ${observed.status}`);
  } catch (error) {
    findings.push({
      id: definition.id,
      title: definition.title,
      severity: definition.severity,
      status: 'unverified',
      expected: definition.expected,
      actual: `probe error: ${error.message.slice(0, 400)}`,
      evidence: 'probe did not complete',
    });
    results.push({
      name: `${definition.id} probe`,
      status: 'unverified',
      error: error.message.slice(0, 400),
    });
    console.error(`UNVERIFIED ${definition.id}: ${error.message.slice(0, 400)}`);
  } finally {
    assert.deepEqual(errors, [], `${definition.id} browser exception`);
    assert.deepEqual(forbidden, [], `${definition.id} external request`);
    await context.close();
  }
}

const goto = (page, route = '/') => page.goto(`${origin}/#${route}`);
const shot = (page, name) =>
  page.screenshot({
    path: path.join(screenshots, `${name}.png`),
    fullPage: true,
    animations: 'disabled',
  });
const openBook = (page) =>
  page.getByRole('button', { name: /Open the book|פתיחת הספר/ }).first().click();
const overflow = (page) =>
  page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
const uiLanguage = async (page, language) => {
  await page.locator('#ui-language').selectOption(language);
  await page.waitForFunction(
    (lang) => document.documentElement.lang === lang,
    language,
  );
};
const colorRGB = (value) => {
  const match = value.match(/rgba?\(([^)]+)\)/);
  assert(match, `unexpected color ${value}`);
  return match[1].split(',').slice(0, 3).map((part) => Number(part.trim()));
};
const luminance = ([r, g, b]) => {
  const channel = (v) => {
    const s = v / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
};
const contrast = (a, b) => {
  const la = luminance(colorRGB(a));
  const lb = luminance(colorRGB(b));
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
};
const hexColor = (hex) => {
  const parts = hex.match(/../g).map((value) => parseInt(value, 16));
  return `rgb(${parts[0]}, ${parts[1]}, ${parts[2]})`;
};

// ---------------------------------------------------------------------------
// Known-finding probes: measure current behavior, never assert the defect.
// ---------------------------------------------------------------------------

await probe(
  {
    id: 'UX-01',
    title: 'Hebrew physical cover binding side',
    severity: 'P1',
    expected: 'Hebrew cover spine, hinge and depth cues sit on the physical right.',
  },
  async (page) => {
    const measurements = {};
    for (const language of ['he', 'en']) {
      await goto(page, `/read/sample-moon-fox-${language}`);
      await page.locator('.cover-on-table .book-cover').waitFor();
      const cover = await page.locator('.cover-on-table .book-cover').boundingBox();
      const spine = await page.locator('.cover-on-table .book-spine').boundingBox();
      measurements[language] = {
        hinge: await page.locator('.cover-on-table').getAttribute('data-hinge'),
        spineSide:
          spine.x + spine.width / 2 < cover.x + cover.width / 2 ? 'left' : 'right',
        spineWithinCover:
          spine.x >= cover.x - 1 && spine.x + spine.width <= cover.x + cover.width + 1,
      };
    }
    await goto(page, '/read/sample-moon-fox-he');
    await shot(page, 'UX-01-hebrew-cover-spine');
    const resolved =
      measurements.he.spineSide === 'right' && measurements.he.hinge === 'right';
    return {
      status: resolved ? 'resolved' : 'present',
      actual: `he hinge=${measurements.he.hinge}, spine=${measurements.he.spineSide}; en hinge=${measurements.en.hinge}, spine=${measurements.en.spineSide}`,
      evidence: 'bounding boxes of .cover-on-table .book-cover and .book-spine',
      measurements,
    };
  },
);

await probe(
  {
    id: 'UX-02',
    title: 'Reader tool labels after interface-language change',
    severity: 'P2',
    expected: 'All reader labels switch with the interface locale while the book language keeps direction.',
  },
  async (page) => {
    await goto(page, '/read/sample-moon-fox-en');
    await page.locator('.reader-tools').waitFor();
    await uiLanguage(page, 'he');
    const afterHebrew = await page.locator('.reader-tools').innerText();
    const readerHint = await page.locator('.hint').first().innerText();
    const arabicDirection = await page.locator('.physical-book').getAttribute('dir');
    await uiLanguage(page, 'en');
    const afterEnglish = await page.locator('.reader-tools').innerText();
    await shot(page, 'UX-02-reader-locale-switch');
    const staleHebrewUI =
      afterHebrew.includes('Page overview') ||
      afterHebrew.includes('Read fullscreen') ||
      afterHebrew.includes('Two-page spread');
    const staleEnglishUI =
      afterEnglish.includes('מפת עמודים') ||
      afterEnglish.includes('קריאה במסך מלא');
    return {
      status: !staleHebrewUI && !staleEnglishUI ? 'resolved' : 'present',
      actual: `after he: "${afterHebrew.replace(/\s+/g, ' ')}"; hint="${readerHint}"; after en: "${afterEnglish.replace(/\s+/g, ' ')}"; book dir=${arabicDirection}`,
      evidence: 'immediate label snapshot after #ui-language change, before any other interaction',
    };
  },
);

await probe(
  {
    id: 'UX-03',
    title: 'Literal dedication is treated as template syntax',
    severity: 'P2',
    expected: 'A user-written dedication is preserved byte-for-byte; substitution applies only to authored template text.',
  },
  async (page) => {
    const dedication = 'Dear {{name}}, from {{companion}}. <b>literal</b> 🌙';
    await goto(page, '/personalize/sky-whale');
    await page.locator('#personal-name').fill('Maya');
    await page.locator('#personal-dedication').fill(dedication);
    await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
    const preview = await page
      .locator('.personal-preview .spread-words p')
      .innerText();
    await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
    await openBook(page);
    const saved = await page.locator('.folio-page .spread-words p').first().innerText();
    await shot(page, 'UX-03-dedication-literal');
    const resolved = preview === dedication && saved === dedication;
    return {
      status: resolved ? 'resolved' : 'present',
      actual: `preview="${preview}"; saved="${saved}"`,
      evidence: `authored input="${dedication}"`,
    };
  },
);

await probe(
  {
    id: 'UX-04',
    title: 'Preview round-trip clears the unsaved-edit guard',
    severity: 'P2',
    expected: 'Preview and return keeps the dirty revision and its beforeunload guard.',
  },
  async (page) => {
    const prevented = () =>
      page.evaluate(() => {
        const event = new Event('beforeunload', { cancelable: true });
        window.dispatchEvent(event);
        return event.defaultPrevented;
      });
    await goto(page, '/studio/new');
    await page.getByLabel('Book title').fill('QA unsaved regression');
    await page.locator('#page-text').fill('A private synthetic draft');
    const before = await prevented();
    await page.getByRole('button', { name: 'Preview book', exact: true }).click();
    await page.getByRole('link', { name: 'Continue editing', exact: true }).click();
    await page.locator('#page-text').waitFor();
    const textAfter = await page.locator('#page-text').inputValue();
    const after = await prevented();
    await shot(page, 'UX-04-preview-dirty-state');
    const resolved = before === true && after === true && textAfter === 'A private synthetic draft';
    return {
      status: resolved ? 'resolved' : 'present',
      actual: `before=${before}; after=${after}; text preserved=${textAfter === 'A private synthetic draft'}`,
      evidence: 'cancelable beforeunload event dispatched on the editor before/after preview',
    };
  },
);

await probe(
  {
    id: 'UX-05',
    title: 'Companion change has inspectable live-preview feedback',
    severity: 'P3',
    expected: 'Changing the companion either updates the visible page or offers page navigation to the affected page.',
  },
  async (page) => {
    await goto(page, '/personalize/sky-whale');
    await page.locator('#personal-name').fill('Maya');
    await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
    const before = await page.locator('.personal-preview').innerText();
    await page.locator('#personal-companion').selectOption('rabbit');
    const after = await page.locator('.personal-preview').innerText();
    const pageControls = await page
      .locator('.personal-preview')
      .getByRole('button', { name: /page|עמוד/i })
      .count();
    await page.locator('#personal-dedication').fill('To Maya');
    const withDedication = await page.locator('.personal-preview').innerText();
    await shot(page, 'UX-05-companion-preview');
    const resolved = before !== after || pageControls > 0;
    return {
      status: resolved ? 'resolved' : 'present',
      actual: `preview changed=${before !== after}; page controls=${pageControls}; with dedication only first page rendered=${withDedication.includes('To Maya') && !withDedication.includes('whale')}`,
      evidence: 'live preview text and available preview navigation after companion change',
    };
  },
);

await probe(
  {
    id: 'UX-06',
    title: 'Cover title contrast against illustrated artwork',
    severity: 'P1',
    expected: 'Every title line meets at least the 3:1 large-text contrast minimum against the actual artwork behind it.',
  },
  async (page) => {
    const samples = {};
    for (const language of ['en', 'he']) {
      await goto(page, `/read/sample-moon-fox-${language}`);
      await page.locator('.cover-on-table .book-cover').waitFor();
      const geometry = await page
        .locator('.cover-on-table .book-cover')
        .evaluate(async (cover) => {
          const title = cover.querySelector('.cover-heading strong');
          const image = cover.querySelector('img');
          const coverRect = cover.getBoundingClientRect();
          const titleRect = title.getBoundingClientRect();
          const imageRect = image.getBoundingClientRect();
          const overlap = Math.max(
            0,
            Math.min(titleRect.bottom, imageRect.bottom) -
              Math.max(titleRect.top, imageRect.top),
          );
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(coverRect.width);
          canvas.height = Math.round(coverRect.height);
          const context = canvas.getContext('2d');
          const loaded = new Image();
          loaded.src = image.currentSrc || image.src;
          await loaded.decode();
          context.drawImage(loaded, 0, 0, canvas.width, canvas.height);
          const x = Math.max(
            0,
            Math.min(
              canvas.width - 1,
              Math.round(titleRect.left - coverRect.left + titleRect.width / 2),
            ),
          );
          const y = Math.max(
            0,
            Math.min(
              canvas.height - 1,
              Math.round(titleRect.top - coverRect.top + titleRect.height * 0.72),
            ),
          );
          const pixel = context.getImageData(x, y, 1, 1).data;
          return {
            overlap,
            color: getComputedStyle(title).color,
            fontSize: getComputedStyle(title).fontSize,
            fontWeight: getComputedStyle(title).fontWeight,
            sampledArtwork: `rgb(${pixel[0]}, ${pixel[1]}, ${pixel[2]})`,
            samplePoint: { x, y },
          };
        });
      samples[language] = {
        ...geometry,
        authoredArtContrast: contrast(geometry.color, hexColor('414271')),
        sampledArtContrast: contrast(geometry.color, geometry.sampledArtwork),
      };
      await shot(page, `UX-06-cover-contrast-${language}`);
    }
    const worst = Math.min(
      samples.en.authoredArtContrast,
      samples.he.authoredArtContrast,
    );
    return {
      status: worst >= 3 ? 'resolved' : 'present',
      actual: `en color=${samples.en.color} on authored #414271 => ${samples.en.authoredArtContrast.toFixed(3)}:1 (sampled ${samples.en.sampledArtwork} => ${samples.en.sampledArtContrast.toFixed(3)}:1); he => ${samples.he.authoredArtContrast.toFixed(3)}:1; overlap=${samples.en.overlap.toFixed(1)}px`,
      evidence: 'computed title color, title/image overlap, and canvas sample of the artwork behind the title',
      samples,
    };
  },
);

await probe(
  {
    id: 'UX-07',
    title: 'Cart link accessible name does not contain its visible text',
    severity: 'P2',
    expected: 'The accessible name includes the visible label and quantity so speech input can activate it by what is shown.',
  },
  async (page) => {
    await goto(page, '/');
    const link = await page.locator('.bag-link').evaluate((element) => ({
      ariaLabel: element.getAttribute('aria-label'),
      visibleText: element.innerText.replace(/\s+/g, ' ').trim(),
    }));
    const report = await new AxeBuilder({ page })
      .withTags(['wcag21a'])
      .analyze();
    const hits = report.violations.filter(
      (violation) => violation.id === 'label-content-name-mismatch',
    );
    await shot(page, 'UX-07-cart-accessible-name');
    return {
      status: hits.length ? 'present' : 'resolved',
      actual: `aria-label="${link.ariaLabel}"; visible="${link.visibleText}"; axe hits=${hits.length}`,
      evidence: 'axe label-content-name-mismatch plus computed labels on the header cart link',
    };
  },
);

await probe(
  {
    id: 'UX-08', title: 'Presentation choice has no visible output effect', severity: 'P3',
    expected: 'An offered presentation option has a documented effect or is clearly identified as metadata-only.',
  },
  async page => {
    await goto(page, '/personalize/sky-whale');
    const vector = () => page.locator('.character-intro [data-character]').evaluate(element => {
      const clone = element.cloneNode(true); clone.removeAttribute('data-character'); return clone.outerHTML;
    });
    const before = await vector();
    await page.getByRole('button', { name: 'Girl', exact: true }).click();
    const after = await vector();
    const selected = JSON.parse(await page.locator('.character-intro [data-character]').getAttribute('data-character'));
    await shot(page, 'UX-08-presentation-no-visible-effect');
    return { status: before === after && selected.presentation === 'girl' ? 'present' : 'resolved',
      actual: `selected presentation=${selected.presentation}; rendered SVG changed=${before !== after}`,
      evidence: 'SVG comparison excluding the data-character metadata attribute; no gendered design prescribed' };
  },
);

// ---------------------------------------------------------------------------
// Functional regressions.
// ---------------------------------------------------------------------------

for (const language of ['en', 'he']) {
  await check(
    `reader physical spread order, geometry and backwards keys ${language}`,
    async (page) => {
      const rtl = language === 'he';
      await goto(page, `/read/sample-moon-fox-${language}`);
      await page.locator('.cover-on-table .book-cover').waitFor();
      await openBook(page);
      const first = await page.locator('[data-page-number="1"]').boundingBox();
      const blank = await page.locator('.inside-cover').first().boundingBox();
      assert(rtl ? first.x < blank.x : first.x > blank.x, 'opening page side');
      const seen = [1];
      while (
        !(await page
          .getByRole('button', { name: /Next page|העמוד הבא/ })
          .isDisabled())
      ) {
        await page.keyboard.press(rtl ? 'ArrowLeft' : 'ArrowRight');
        const visible = await page.locator('[data-page-number]').evaluateAll((elements) =>
          elements.map((element) => ({
            number: Number(element.getAttribute('data-page-number')),
            x: element.getBoundingClientRect().x,
          })),
        );
        seen.push(...visible.map((item) => item.number));
        if (visible.length === 2) {
          assert(
            rtl ? visible[0].x > visible[1].x : visible[0].x < visible[1].x,
            `spread geometry on page ${visible.map((item) => item.number).join('/')}`,
          );
        }
      }
      assert.deepEqual(seen, [1, 2, 3, 4, 5, 6]);
      await page.keyboard.press(rtl ? 'ArrowRight' : 'ArrowLeft');
      assert.deepEqual(
        await page
          .locator('[data-page-number]')
          .evaluateAll((elements) =>
            elements.map((element) => Number(element.getAttribute('data-page-number'))),
          ),
        [4, 5],
      );
      const counter = await page.locator('.page-counter').innerText();
      assert(counter.includes('4') && counter.includes('5'));
      assert(!(await overflow(page)));
      await shot(page, `reader-latest-${language}-desktop`);
    },
  );

  await check(
    `reader native touch single-page direction ${language}`,
    async (page, context) => {
      const rtl = language === 'he';
      await goto(page, `/read/sample-moon-fox-${language}`);
      await openBook(page);
      assert.equal(await page.locator('[data-page-number]').count(), 1);
      await page.locator('.physical-book').scrollIntoViewIfNeeded();
      const box = await page.locator('.physical-book').boundingBox();
      const start = rtl ? 90 : 280;
      const end = rtl ? 280 : 90;
      const y = Math.max(80, Math.min(500, box.y + 100));
      const session = await context.newCDPSession(page);
      await session.send('Input.dispatchTouchEvent', {
        type: 'touchStart',
        touchPoints: [{ x: start, y }],
      });
      await session.send('Input.dispatchTouchEvent', {
        type: 'touchMove',
        touchPoints: [{ x: end, y }],
      });
      await session.send('Input.dispatchTouchEvent', {
        type: 'touchEnd',
        touchPoints: [],
      });
      await page.locator('[data-page-number="2"]').waitFor();
      assert(!(await overflow(page)));
    },
    { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true },
  );
}

await check('reader direction stays book-owned under the opposite interface locale', async (page) => {
  for (const language of ['en', 'he']) {
    await goto(page, `/read/sample-moon-fox-${language}`);
    await uiLanguage(page, language === 'he' ? 'en' : 'he');
    await openBook(page);
    await page.keyboard.press(language === 'he' ? 'ArrowLeft' : 'ArrowRight');
    const boxes = await page.locator('[data-page-number]').evaluateAll((elements) =>
      elements.map((element) => ({
        number: Number(element.dataset.pageNumber),
        x: element.getBoundingClientRect().x,
      })),
    );
    assert.deepEqual(boxes.map((box) => box.number), [2, 3]);
    assert(
      language === 'he' ? boxes[0].x > boxes[1].x : boxes[0].x < boxes[1].x,
      `${language} spread direction under opposite UI`,
    );
    assert.equal(
      await page.locator('.physical-book').getAttribute('dir'),
      language === 'he' ? 'rtl' : 'ltr',
    );
    assert.equal(
      await page.locator('.physical-spread').getAttribute('lang'),
      language,
    );
  }
});

await check('template capabilities, cover language and ordinary dedication parity', async (page) => {
  await goto(page, '/personalize/small-hero');
  assert.equal(await page.locator('#personal-companion').count(), 0);
  assert.equal(await page.locator('#personal-color').count(), 0);
  await page.locator('#personal-name').fill('Zoë');
  await page.locator('#personal-outfit').selectOption('striped');
  assert(
    (await page.locator('.personal-preview .book-cover img').getAttribute('src')).endsWith(
      'hero-striped.svg',
    ),
  );

  await goto(page, '/personalize/sky-whale');
  assert.equal(await page.locator('#personal-companion').count(), 1);
  assert.equal(await page.locator('#personal-color').count(), 1);
  await page.locator('#personal-name').fill('אוֹר Lee');
  await page.locator('#personal-color').selectOption('#c9c0e0');
  assert.equal(
    await page.locator('.personal-preview .book-cover').evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ),
    'rgb(201, 192, 224)',
  );
  await page.locator('#personal-dedication').fill('For the moon and stars 🌙');
  await page.locator('#template-language').selectOption('he');
  assert.equal(
    await page.locator('.personal-preview .book-cover').getAttribute('dir'),
    'rtl',
  );
  await page.getByRole('button', { name: 'Peek inside', exact: true }).click();
  const preview = await page
    .locator('.personal-preview .spread-words p')
    .innerText();
  await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
  await openBook(page);
  assert.equal(
    await page.locator('.folio-page .spread-words p').first().innerText(),
    preview,
  );
  assert.equal(await page.locator('h1').first().getAttribute('lang'), 'he');

  await goto(page, '/personalize/moon-fox');
  assert.equal(await page.locator('#personal-outfit').count(), 0);
  assert.equal(await page.locator('#personal-companion').count(), 0);
});

await check('character builder state, keyboard use, saved persistence and locale', async (page) => {
  await goto(page, '/personalize/sky-whale');
  await page.locator('#personal-name').fill('Maya');
  await page.getByRole('button', { name: 'Deep', exact: true }).click();
  await page.getByRole('button', { name: 'Girl', exact: true }).click();
  await page.getByRole('button', { name: 'Black', exact: true }).click();
  await page.getByRole('button', { name: 'Green', exact: true }).click();
  await page.getByRole('button', { name: 'Sailor', exact: true }).click();
  await page.getByRole('button', { name: 'Long', exact: true }).click();
  await page.getByLabel('Glasses', { exact: true }).check();
  await page.getByLabel('Freckles', { exact: true }).check();
  await page.getByRole('button', { name: 'Adventure hat' }).focus();
  await page.keyboard.press('Enter');
  assert.equal(
    await page.getByRole('button', { name: 'Adventure hat' }).getAttribute('aria-pressed'),
    'true',
  );
  const character = JSON.parse(
    await page.locator('.character-intro [data-character]').getAttribute('data-character'),
  );
  assert.equal(character.skin, 'deep');
  assert.equal(character.presentation, 'girl');
  assert.equal(character.hair, 'black');
  assert.equal(character.eye, 'greenEyes');
  assert.equal(character.outfit, 'sailor');
  assert.equal(character.hairstyle, 'longHair');
  assert.equal(character.glasses, true);
  assert.equal(character.freckles, true);
  assert.equal(character.accessory, 'hat');
  await shot(page, 'character-builder-latest');

  await uiLanguage(page, 'he');
  assert.equal(
    await page.getByRole('button', { name: 'כהה', exact: true }).getAttribute('aria-pressed'),
    'true',
  );
  assert(
    (await page.locator('.character-intro h2').innerText()).includes('הדמות'),
  );

  await page.getByRole('button', { name: 'שמירה בספרים שלי', exact: true }).click();
  await page.locator('.cover-avatar').waitFor();
  assert.equal(await page.locator('.cover-avatar').count(), 1);
  const savedCharacter = JSON.parse(
    await page.locator('.cover-avatar [data-character]').getAttribute('data-character'),
  );
  assert.equal(savedCharacter.skin, 'deep');
  assert.equal(savedCharacter.accessory, 'hat');
  await openBook(page);
  assert.equal(await page.locator('.folio-page .page-avatar').count(), 1);
});

await check('fullscreen enter/exit and reduced motion on latest reader', async page => {
  await goto(page, '/read/sample-moon-fox-he');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  assert.equal(await page.locator('.cover-on-table .book-cover').evaluate(el => getComputedStyle(el).transform), 'none');
  await openBook(page);
  assert.equal(await page.locator('.physical-spread').evaluate(el => getComputedStyle(el).animationName), 'none');
  await page.getByRole('button', { name: 'Read fullscreen', exact: true }).click();
  await page.waitForFunction(() => !!document.fullscreenElement);
  await page.getByRole('button', { name: 'Leave fullscreen', exact: true }).click();
  await page.waitForFunction(() => !document.fullscreenElement);
});

await check('keyboard skip, creation routes, and mobile menu Escape on latest frontend', async page => {
  await goto(page);
  await page.keyboard.press('Tab');
  assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
  await page.keyboard.press('Enter');
  assert.equal(await page.locator(':focus').getAttribute('id'), 'main-content');
  for (const route of ['/create/ai', '/books', '/studio/new']) {
    await goto(page, route); await page.locator('main').waitFor();
  }
  await page.setViewportSize({ width: 360, height: 844 });
  await page.getByRole('button', { name: 'Menu', exact: true }).click();
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('button', { name: 'Menu', exact: true }).evaluate(el => el === document.activeElement), true);
});

await check('manual editor save, reorder and reopen without warning loss', async (page) => {
  const prevented = () =>
    page.evaluate(() => {
      const event = new Event('beforeunload', { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    });
  await goto(page, '/studio/new');
  await page.getByLabel('Book title').fill('QA ordered regression');
  await page.locator('#page-text').fill('First page');
  await page.getByRole('button', { name: /Add a page/ }).click();
  await page.locator('#page-text').fill('Second page');
  await page.getByRole('button', { name: 'Move earlier' }).click();
  assert.equal(await prevented(), true);
  await page.getByRole('button', { name: 'Save draft in this tab', exact: true }).click();
  assert.equal(await prevented(), false);
  await page.getByRole('link', { name: 'My books', exact: true }).last().click();
  await page
    .locator('.library-card')
    .filter({ hasText: 'QA ordered regression' })
    .getByRole('link', { name: /Continue editing/ })
    .click();
  assert.equal(await page.locator('#page-text').inputValue(), 'Second page');
  assert.equal(await page.locator('.page-rail li').count(), 2);
  assert.equal(await prevented(), false);
});

await check('demo commerce journey: format, cart, discount, decline, confirmation and order history', async (page) => {
  await goto(page, '/personalize/sky-whale');
  await page.locator('#personal-name').fill('Maya Commerce');
  await page.getByRole('button', { name: 'Save to my books', exact: true }).click();
  await openBook(page);
  await page.getByRole('button', { name: 'Choose format & quantity' }).click();
  await page.locator('.format-page').waitFor();

  // Invalid boundary quantity is rejected rather than silently clamped.
  await page.locator('#format-quantity').fill('11');
  await page.getByRole('button', { name: 'Add to bag', exact: true }).click();
  await page.getByRole('alert').waitFor();
  assert.equal(await page.locator('.format-page').count(), 1);

  await page.locator('input[name="format"][value="hardcover"]').check();
  await page.locator('#format-quantity').fill('2');
  await page.getByRole('button', { name: 'Add to bag', exact: true }).click();
  await page.locator('.cart-line').waitFor();
  assert.equal(await page.locator('.cart-line').count(), 1);
  assert.equal(await page.locator('.bag-count').innerText(), '2');
  assert((await page.locator('.order-summary').innerText()).includes('$78.00'));

  await page.locator('.cart-line select').selectOption('1');
  assert.equal(await page.locator('.bag-count').innerText(), '1');
  assert((await page.locator('.order-summary').innerText()).includes('$39.00'));

  await page.getByRole('link', { name: 'Continue as a guest' }).click();
  await page.locator('.checkout-steps').waitFor();
  await page.locator('#promo-code').fill('STORY10');
  await page.getByRole('button', { name: 'Apply', exact: true }).click();
  const totals = await page.locator('.quote-totals').innerText();
  assert(totals.includes('−$3.90') || totals.includes('-$3.90'));
  assert(totals.includes('$40.10'));

  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('alert').waitFor();
  assert.equal(
    await page.evaluate(() => document.activeElement?.getAttribute('aria-invalid')),
    'true',
  );
  await page.getByLabel('First name', { exact: true }).fill('Alex');
  await page.getByLabel('Last name', { exact: true }).fill('Example');
  await page.getByLabel('Email address', { exact: true }).fill('demo@example.test');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel('Street address', { exact: true }).fill('123 Sample Street');
  await page.getByLabel('City', { exact: true }).fill('Example City');
  await page.getByLabel('Postal code', { exact: true }).fill('12345');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByLabel(/Express demonstration delivery/).check();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  assert.equal(await page.locator('input[autocomplete="cc-number"]').count(), 0);
  assert.equal(await page.locator('input[type="password"]').count(), 0);
  await page.getByLabel('Preview a declined simulation').check();
  await page.getByRole('button', { name: 'Simulate order', exact: true }).click();
  await page.getByRole('alert').waitFor();
  assert((await page.getByRole('alert').innerText()).includes('simulation could not finish'));
  assert.equal(await page.locator('.bag-count').innerText(), '1');
  await shot(page, 'commerce-checkout-declined-latest');

  await page.getByLabel('Preview a declined simulation').uncheck();
  await page.getByRole('button', { name: 'Simulate order', exact: true }).click();
  await page.getByRole('heading', { name: 'A little magic, ready for its next chapter.' }).waitFor();
  assert.equal(await page.locator('.bag-count').innerText(), '0');
  assert((await page.locator('main').innerText()).includes('Simulated · not placed'));
  await shot(page, 'commerce-confirmation-latest');

  await page.getByRole('link', { name: 'Your demonstration orders', exact: true }).click();
  await page.getByRole('link', { name: 'View order', exact: true }).click();
  await page.getByRole('heading', { name: 'The details of your keepsake' }).waitFor();
  assert((await page.locator('.order-detail').innerText()).includes('DEMO-'));

  await uiLanguage(page, 'he');
  assert(
    (await page.locator('main h1').innerText()).includes('הפרטים של המזכרת'),
  );
  assert.equal(await page.locator('html').getAttribute('dir'), 'rtl');
  assert(!(await overflow(page)));
});

await check('cart removal, empty states and maximum quantity boundary', async (page) => {
  await goto(page, '/cart');
  await page.getByRole('heading', { name: 'Your next keepsake starts with a story.' }).waitFor();
  await goto(page, '/checkout');
  await page.getByRole('heading', { name: 'Your next keepsake starts with a story.' }).waitFor();
  await goto(page, '/orders');
  await page.getByRole('heading', { name: 'No demonstration orders yet.' }).waitFor();

  await goto(page, '/format/sample-moon-fox-en');
  await page.locator('#format-quantity').fill('10');
  await page.getByRole('button', { name: 'Add to bag', exact: true }).click();
  await page.locator('.cart-line').waitFor();
  await page.getByRole('button', { name: 'Remove', exact: true }).click();
  await page.getByRole('heading', { name: 'Your next keepsake starts with a story.' }).waitFor();
  assert.equal(await page.locator('.bag-count').innerText(), '0');

  await goto(page, '/format/sample-moon-fox-en');
  await page.locator('#format-quantity').fill('10');
  await page.getByRole('button', { name: 'Add to bag', exact: true }).click();
  await page.locator('.cart-line').waitFor();
  await goto(page, '/format/sample-moon-fox-en');
  await page.locator('#format-quantity').fill('1');
  await page.getByRole('button', { name: 'Add to bag', exact: true }).click();
  await page.getByRole('alert').waitFor();
  await page.reload();
  assert.equal(await page.locator('.bag-count').innerText(), '0');
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
});

for (const width of [360, 390, 768, 1024, 1440]) {
  await check(
    `responsive overflow at ${width}px including commerce and reader`,
    async (page) => {
      for (const route of [
        '/',
        '/books',
        '/personalize/sky-whale',
        '/my-books',
        '/studio/demo-draft',
        '/cart',
        '/orders',
        '/format/sample-moon-fox-en',
        '/read/sample-moon-fox-he',
      ]) {
        await goto(page, route);
        await page.locator('main').waitFor();
        if (route.startsWith('/read')) await openBook(page);
        assert(!(await overflow(page)), `${route} overflows at ${width}px`);
      }
      metrics.push({ width, routes: 9, horizontalOverflow: false });
    },
    { viewport: { width, height: 900 } },
  );
}

await check('axe sweep across current routes in both interface locales', async (page) => {
  const routes = [
    '/',
    '/books',
    '/books/sky-whale',
    '/personalize/sky-whale',
    '/my-books',
    '/studio/demo-draft',
    '/read/sample-moon-fox-he',
    '/cart',
    '/orders',
    '/format/sample-moon-fox-en',
    '/checkout',
  ];
  for (const language of ['en', 'he']) {
    for (const route of routes) {
      await goto(page, route);
      await page.locator('main').waitFor();
      await uiLanguage(page, language);
      if (route.startsWith('/read')) await openBook(page);
      const report = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();
      a11y.push({
        scenario: `${language}:${route}`,
        violations: report.violations.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          wcag: violation.tags.filter((tag) => tag.startsWith('wcag')),
          nodes: violation.nodes.map((node) => node.target),
        })),
      });
    }
  }
  const nonCartViolations = a11y
    .flatMap((scenario) =>
      scenario.violations
        .filter((violation) => violation.id !== 'label-content-name-mismatch')
        .map((violation) => ({ scenario: scenario.scenario, id: violation.id })),
    )
    .filter((item, index, list) => list.findIndex((other) => other.id === item.id && other.scenario === item.scenario) === index);
  if (nonCartViolations.length) {
    findings.push({
      id: 'AXE-EXTRA',
      title: 'Additional automated accessibility violations',
      severity: 'P2',
      status: 'present',
      expected: 'No automated WCAG A/AA violations.',
      actual: JSON.stringify(nonCartViolations),
      evidence: 'axe scan of 22 route/locale combinations',
    });
  }
  console.log(
    `axe scenarios=${a11y.length} with violations=${a11y.filter((scenario) => scenario.violations.length).length}`,
  );
});

await browser.close();

const findingCounts = findings.reduce((counts, finding) => {
  counts[finding.status] = (counts[finding.status] ?? 0) + 1;
  return counts;
}, {});
const report = {
  pin,
  snapshot,
  origin,
  generatedAt: new Date().toISOString(),
  environment: {
    node: process.version,
    playwright: '1.64.1',
    axe: '4.14.0',
    chromium: browserVersion,
  },
  results,
  findings,
  a11y,
  metrics,
  externalAttempts,
  summary: {
    passed: results.filter((result) => result.status === 'passed').length,
    failed: results.filter((result) => result.status === 'failed').length,
    inspected: results.filter((result) => result.status === 'inspected').length,
    unverified: results.filter((result) => result.status === 'unverified').length,
    findings: findingCounts,
    a11yScenarios: a11y.length,
    a11yScenariosWithViolations: a11y.filter((scenario) => scenario.violations.length).length,
    externalAttempts: externalAttempts.length,
  },
};
await fs.mkdir(path.dirname(resultsFile), { recursive: true });
await fs.writeFile(resultsFile, JSON.stringify(report, null, 2), 'utf8');
console.log(JSON.stringify(report.summary, null, 2));
if (report.summary.failed || report.summary.unverified) process.exitCode = 1;
