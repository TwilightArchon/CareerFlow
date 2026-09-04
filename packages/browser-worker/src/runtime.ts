import { mkdir } from 'node:fs/promises';

import type {
  BrowserFieldFill,
  FieldMapping,
  FormControl,
  ObservedForm,
} from '@careerflow/contracts';
import { chromium, type BrowserContext, type Page, type Route } from 'playwright-core';

import { requirePublicNavigationUrl } from './security';
import { SYNTHETIC_FORM_HTML, SYNTHETIC_FORM_URL } from './synthetic-form';

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
    return await this.pageStateHash(page);
  }

  async openSyntheticForm(): Promise<ObservedForm> {
    const page = await this.ensurePage();
    await page.goto(SYNTHETIC_FORM_URL, { waitUntil: 'domcontentloaded', timeout: 15_000 });
    return await this.scanCurrentForm();
  }

  async scanCurrentForm(): Promise<ObservedForm> {
    const page = await this.ensurePage();
    const controls = await page.evaluate<Array<Omit<FormControl, 'sensitivity'>>>(() => {
      const elements = Array.from(document.querySelectorAll('input, select, textarea'));
      return elements.flatMap((element, index) => {
        if (!(
          element instanceof HTMLInputElement ||
          element instanceof HTMLSelectElement ||
          element instanceof HTMLTextAreaElement
        ))
          return [];
        if (
          element instanceof HTMLInputElement &&
          ['hidden', 'submit', 'button', 'reset'].includes(element.type)
        )
          return [];
        const controlId = element.id || `careerflow-control-${index}`;
        if (!element.id) element.id = controlId;
        const explicit = document.querySelector(`label[for="${CSS.escape(controlId)}"]`);
        const label = (
          explicit?.textContent ||
          element.closest('label')?.textContent ||
          element.getAttribute('aria-label') ||
          element.getAttribute('placeholder') ||
          element.name ||
          controlId
        )
          .trim()
          .replace(/\s+/g, ' ');
        const inputType = element instanceof HTMLInputElement ? element.type : '';
        const kind: FormControl['kind'] =
          element instanceof HTMLSelectElement
            ? 'select'
            : element instanceof HTMLTextAreaElement
              ? 'textarea'
              : inputType === 'email'
                ? 'email'
                : inputType === 'tel'
                  ? 'tel'
                  : inputType === 'checkbox'
                    ? 'checkbox'
                    : inputType === 'radio'
                      ? 'radio'
                      : inputType === 'file'
                        ? 'file'
                        : 'text';
        return [
          {
            controlId,
            label,
            kind,
            required: element.required,
            options:
              element instanceof HTMLSelectElement
                ? Array.from(element.options)
                    .map((option) => option.text.trim())
                    .filter(Boolean)
                : [],
            autocomplete: element.getAttribute('autocomplete'),
          },
        ];
      });
    });
    const normalized: FormControl[] = controls.map((control) => ({
      ...control,
      sensitivity: classifySensitivity(control.label, control.kind),
    }));
    return {
      pageUrl: page.url(),
      pageStateHash: await this.pageStateHash(page),
      controls: normalized,
    };
  }

  async fillApprovedFields(
    fills: BrowserFieldFill[],
    expectedPageStateHash?: string,
  ): Promise<FieldMapping[]> {
    const page = await this.ensurePage();
    if (expectedPageStateHash && (await this.pageStateHash(page)) !== expectedPageStateHash) {
      throw new Error('The page changed after inspection; a new scan is required');
    }
    const completed: FieldMapping[] = [];
    for (const fill of fills) {
      if (!/^[A-Za-z0-9_-]+$/.test(fill.controlId)) {
        throw new Error('The approved control identifier is invalid');
      }
      const locator = page.locator(`#${fill.controlId}`);
      if ((await locator.count()) !== 1)
        throw new Error('The approved control is no longer unique');
      const current = await locator.inputValue();
      if (current !== fill.value) await locator.fill(fill.value);
      await locator.evaluate((element, rationale) => {
        element.setAttribute('data-careerflow-filled', 'true');
        element.setAttribute('data-careerflow-explanation', rationale);
      }, fill.rationale);
      completed.push({
        controlId: fill.controlId,
        canonicalPath: fill.canonicalPath,
        source: 'deterministic',
        confidence: 0.98,
        sensitivity: 'ordinary',
        decision: 'auto_fill',
        rationale: fill.rationale,
      });
    }
    return completed;
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
      if (route.request().url() === SYNTHETIC_FORM_URL) {
        await route.fulfill({
          status: 200,
          contentType: 'text/html; charset=utf-8',
          body: SYNTHETIC_FORM_HTML,
        });
        return;
      }
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

  private async pageStateHash(page: Page): Promise<string> {
    return await page.evaluate(async () => {
      const formState = Array.from(document.querySelectorAll('input, select, textarea'))
        .slice(0, 500)
        .map((element) => {
          if (!(
            element instanceof HTMLInputElement ||
            element instanceof HTMLSelectElement ||
            element instanceof HTMLTextAreaElement
          )) {
            return '';
          }
          const checked = element instanceof HTMLInputElement ? String(element.checked) : '';
          return `${element.id}\u0000${element.value}\u0000${checked}`;
        })
        .join('\u0001');
      const source = `${window.location.href}\n${document.title}\n${document.body.innerText.slice(0, 20_000)}\n${formState}`;
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(source));
      return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join(
        '',
      );
    });
  }
}

export function classifySensitivity(
  label: string,
  kind: FormControl['kind'],
): FormControl['sensitivity'] {
  const normalized = label.toLowerCase();
  if (normalized.includes('authorization') || normalized.includes('sponsorship')) return 'legal';
  if (kind === 'email' || kind === 'tel' || normalized.includes('address')) return 'sensitive';
  return 'ordinary';
}
