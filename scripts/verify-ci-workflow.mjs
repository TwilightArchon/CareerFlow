import { readFile } from 'node:fs/promises';

const workflowPath = new URL('../.github/workflows/ci.yml', import.meta.url);
const workflow = await readFile(workflowPath, 'utf8');

function actionMajor(action) {
  const match = workflow.match(new RegExp(`uses: ${action.replace('/', '\\/')}@v(\\d+)`));
  if (!match) {
    throw new Error(`CI workflow is missing ${action}`);
  }
  return Number(match[1]);
}

const pnpmSetupIndex = workflow.indexOf('uses: pnpm/action-setup@');
const nodeSetupIndex = workflow.indexOf('uses: actions/setup-node@');

if (pnpmSetupIndex > nodeSetupIndex) {
  throw new Error(
    'pnpm/action-setup must run before actions/setup-node when setup-node uses cache: pnpm',
  );
}

if (actionMajor('actions/checkout') < 5 || actionMajor('actions/setup-node') < 5) {
  throw new Error(
    "GitHub's checkout and setup-node actions must use Node 24-backed major versions",
  );
}

if (actionMajor('pnpm/action-setup') < 4) {
  throw new Error('pnpm/action-setup must use a pnpm 10-compatible maintained major version');
}

if (
  !workflow.includes('uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0')
) {
  throw new Error('setup-uv must use the reviewed immutable v8.1.0 action revision');
}

if (!workflow.includes('node-version-file: .node-version')) {
  throw new Error('CI must install the repository-pinned Node.js version');
}

if (!workflow.includes('pnpm install --frozen-lockfile')) {
  throw new Error('CI must install JavaScript dependencies from the committed lockfile');
}

console.log('CI workflow setup order and pinned toolchain are valid.');
