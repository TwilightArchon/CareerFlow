import { mkdir } from 'node:fs/promises';

import { chromium, type BrowserContext, type Page, type Route } from 'playwright-core';

import { requirePublicNavigationUrl } from './security';

const DEFAULT_CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

export class BrowserRuntime {
  private context: BrowserContext | undefined;
  private page: Page | undefined;

  constructor(
    private readonly profileDir: string,
    private readonly executablePath = process.env.CAREERFLOW_CHROME_PATH ?? DEFAULT_CHROME,
  ) {}

  async navigate(rawUrl: string): Promise<string> {
    const url = await requirePublicNavigationUrl(rawUrl);
    const page = await this.ensurePage();
    await page.goto(url.toString(), { waitUntil: 'domcontentloaded', timeout: 45_000 });
    return await page.evaluate(() => {
      const source = `${window.location.href}\n${document.title}\n${document.body.innerText.slice(0, 20_000)}`;
      let hash = 2166136261;
      for (let index = 0; index < source.length; index += 1) {
        hash ^= source.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16).padStart(8, '0');
    });
  }

  async close(): Promise<void> {
    await this.context?.close();
    this.context = undefined;
    this.page = undefined;
  }

  private async ensurePage(): Promise<Page> {
    if (this.page && !this.page.isClosed()) return this.page;
    await mkdir(this.profileDir, { recursive: true, mode: 0o700 });
    this.context = await chromium.launchPersistentContext(this.profileDir, {
      executablePath: this.executablePath,
      headless: false,
      viewport: null,
      args: ['--no-first-run', '--no-default-browser-check'],
    });
    await this.context.route('**/*', async (route: Route) => {
      try {
        await requirePublicNavigationUrl(route.request().url());
        await route.continue();
      } catch {
        await route.abort('blockedbyclient');
      }
    });
    this.page = this.context.pages()[0] ?? (await this.context.newPage());
    return this.page;
  }
}
