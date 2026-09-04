import { existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { BrowserRuntime } from '../src/runtime';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const enabled = process.env.CAREERFLOW_BROWSER_INTEGRATION === '1' && existsSync(CHROME);

describe.skipIf(!enabled)('visible browser runtime integration', () => {
  let profileDir: string;
  let runtime: BrowserRuntime;

  beforeAll(async () => {
    profileDir = await mkdtemp(join(tmpdir(), 'careerflow-browser-test-'));
    runtime = new BrowserRuntime(profileDir, CHROME);
  });

  afterAll(async () => {
    await runtime.close();
    await rm(profileDir, { recursive: true, force: true });
  });

  it('opens, scans, and fills the app-owned form without a submit action', async () => {
    const form = await runtime.openSyntheticForm();

    expect(form.pageUrl).toBe('https://synthetic.careerflow.invalid/application');
    expect(form.controls).toHaveLength(12);
    expect(form.controls.find((item) => item.controlId === 'email')?.sensitivity).toBe('sensitive');
    expect(form.controls.find((item) => item.controlId === 'sponsorship')?.sensitivity).toBe(
      'legal',
    );

    const filled = await runtime.fillApprovedFields(
      [
        {
          controlId: 'first-name',
          canonicalPath: 'identity.first_name',
          value: 'Synthetic',
          evidenceIds: ['87c02b80-07e2-4fe1-b5d6-cb2553035ff5'],
          rationale: 'Autocomplete metadata identifies identity.first_name.',
        },
      ],
      form.pageStateHash,
    );

    expect(filled).toHaveLength(1);
    expect(filled[0]?.decision).toBe('auto_fill');
    expect((await runtime.scanCurrentForm()).pageStateHash).not.toBe(form.pageStateHash);
    await expect(
      runtime.fillApprovedFields(
        [
          {
            controlId: 'last-name',
            canonicalPath: 'identity.last_name',
            value: 'Candidate',
            evidenceIds: ['87c02b80-07e2-4fe1-b5d6-cb2553035ff5'],
            rationale: 'Autocomplete metadata identifies identity.last_name.',
          },
        ],
        form.pageStateHash,
      ),
    ).rejects.toThrow('page changed after inspection');
  });
});
