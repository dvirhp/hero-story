// Optional isolated tooling; no changes to application dependencies or servers.
import { defineConfig } from '@playwright/test';

const baseURL = process.env.STORYFORGE_E2E_URL;
if (baseURL) {
  const url = new URL(baseURL);
  if (!['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('QA browser checks require an explicitly started local fake-only frontend');
  }
}
export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  retries: 0,
  workers: 1,
  use: { baseURL, trace: 'off', screenshot: 'off', video: 'off' },
  reporter: 'list',
});
