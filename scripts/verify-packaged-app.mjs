import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { extractFile, listPackage } from '@electron/asar';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const appBundle =
  process.argv[2] ?? join(root, 'apps', 'desktop', 'dist', 'mac-arm64', 'CareerFlow.app');
const archive = join(appBundle, 'Contents', 'Resources', 'app.asar');
const embeddedPython = join(
  appBundle,
  'Contents',
  'Resources',
  'python-runtime',
  'bin',
  'python3.13',
);

if (!existsSync(archive)) {
  throw new Error(`Packaged app archive was not found at ${archive}`);
}
if (!existsSync(embeddedPython)) {
  throw new Error(`Packaged embedded Python was not found at ${embeddedPython}`);
}

const pythonImportCheck = spawnSync(
  embeddedPython,
  ['-c', 'import cryptography, docx, fastapi, pypdf, sqlalchemy'],
  {
    encoding: 'utf8',
    env: { ...process.env, PYTHONNOUSERSITE: '1' },
  },
);
if (pythonImportCheck.status !== 0) {
  throw new Error(
    `Packaged Python runtime is missing a required module: ${pythonImportCheck.stderr}`,
  );
}

const entries = new Set(listPackage(archive, { isPack: false }));
const requiredEntries = [
  '/node_modules/@careerflow/contracts/dist/index.js',
  '/node_modules/@careerflow/browser-worker/dist/index.js',
  '/node_modules/playwright-core/package.json',
  '/node_modules/ws/package.json',
  '/out/main/index.js',
  '/out/preload/index.cjs',
];

for (const entry of requiredEntries) {
  if (!entries.has(entry)) throw new Error(`Packaged app is missing runtime entry ${entry}`);
}

const mainBundle = extractFile(archive, 'out/main/index.js').toString('utf8');
if (/from\s+["']@careerflow\/contracts["']/.test(mainBundle)) {
  throw new Error('Electron main still imports the workspace contracts package at runtime');
}

if (entries.has('/out/preload/index.mjs')) {
  throw new Error('Packaged sandboxed preload must be CommonJS, not ESM');
}

const preloadBundle = extractFile(archive, 'out/preload/index.cjs').toString('utf8');
if (!preloadBundle.includes('contextBridge.exposeInMainWorld')) {
  throw new Error('Packaged preload does not expose the CareerFlow renderer bridge');
}

const contractPackage = JSON.parse(
  extractFile(archive, 'node_modules/@careerflow/contracts/package.json').toString('utf8'),
);
if (contractPackage.exports?.['.']?.import !== './dist/index.js') {
  throw new Error('Packaged contracts do not resolve to compiled JavaScript');
}

readFileSync(join(appBundle, 'Contents', 'MacOS', 'CareerFlow'));
process.stdout.write('Packaged CareerFlow runtime layout is valid.\n');
