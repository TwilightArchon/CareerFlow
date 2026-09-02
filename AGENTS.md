# CareerFlow Agent Instructions

## Project summary

CareerFlow is a desktop-first, supervised job-application agent. A user provides a job URL; the app extracts the posting, prepares evidence-grounded application material, controls a visible browser to register or sign in, fills the application, uploads documents, and records the outcome. It pauses when a step requires human judgment or cannot be completed safely.

The canonical product definition is `docs/PROJECT.md`. The documentation map is `docs/INDEX.md`.

## Mandatory context workflow

Before changing code, configuration, schemas, prompts, tests, or behavior:

1. Read `docs/INDEX.md`.
2. Read `docs/PROJECT.md` and `docs/ARCHITECTURE.md` when the change affects product behavior, system boundaries, data flow, or technology choices.
3. Read every feature document listed in `docs/INDEX.md` that relates to the change.
4. Read `TODO.md` to understand the current phase and avoid building later-stage infrastructure prematurely.
5. Read `docs/TROUBLESHOOTING.md` before diagnosing a regression, packaging failure, startup failure, or previously encountered symptom.
6. If a capability has no feature document, create one from `docs/templates/FEATURE.md` before implementing it and add it to `docs/INDEX.md`.

Do not assume all Markdown files are automatically loaded. Explicitly open the relevant files before editing.

## Documentation synchronization contract

Documentation is part of the implementation. In the same change that modifies a capability:

- Update its file in `docs/features/` when behavior, inputs, outputs, states, errors, approvals, security boundaries, or acceptance criteria change.
- Update `docs/ARCHITECTURE.md` for component, dependency, storage, interface, or data-flow changes.
- Add or update an ADR in `docs/adr/` for decisions that are expensive to reverse.
- Update `TODO.md` when work is completed, added, removed, or re-scoped.
- Update `docs/INDEX.md` when documentation files are added, renamed, or removed.
- Update `README.md` when setup, major features, or the product summary changes.
- Add or update `docs/TROUBLESHOOTING.md` when a significant problem is confirmed, resolved, mitigated, or found still open. Include root cause and verification evidence; do not record guesses as facts.

Never mark a TODO or acceptance criterion complete without verification evidence. If code and documentation disagree, stop and reconcile them before continuing.

## Product boundaries

- Never fabricate candidate experience, credentials, dates, skills, or answers.
- Never bypass CAPTCHA, two-factor authentication, anti-bot controls, rate limits, or platform restrictions.
- Pause for ambiguous, sensitive, legal, demographic, or consent-dependent questions unless the user supplied an explicit reusable answer and policy permits its use.
- Submission is permitted only inside a user-authorized run and only when all required answers pass policy checks. Otherwise pause at review.
- Keep browser activity visible and provide a clear pause, resume, and cancel path.
- Store credentials and tokens in the operating-system keychain, not in source files, logs, prompts, or the application database.
- Treat resumes, application answers, email content, and browser sessions as sensitive personal data.

## Engineering expectations

- Prefer deterministic adapters and validation before model-based interpretation.
- Give every long-running application run an explicit state machine, durable checkpoints, retries, timeouts, and idempotency keys.
- Use typed schemas at all process and network boundaries.
- Record provenance for generated claims and explain why each field was filled.
- Add tests and evaluation cases for every fixed regression.
- Trace model calls, tool calls, state transitions, latency, token usage, errors, and user interventions without logging secrets or unnecessary PII.
- Keep provider-specific ATS logic behind adapter interfaces; the generic semantic fallback must not contain platform-specific selectors.

## Current implementation status

The repository has an executable foundation. It includes the Electron/React desktop shell, authenticated FastAPI service, canonical Pydantic/OpenAPI contracts, generated TypeScript definitions, SQLite workflow events, policy gates, a supervised Playwright worker, and OpenTelemetry instrumentation.

Verified commands:

- `pnpm install`: install the JavaScript workspace from `pnpm-lock.yaml`.
- `uv sync --project services/agent`: install the Python service from `uv.lock`.
- `pnpm build`: build contracts, browser worker, desktop main/preload, and renderer.
- `pnpm test`: run TypeScript and Python tests.
- `pnpm check`: run formatting, TypeScript, and Ruff checks.
- `pnpm python:typecheck`: run strict mypy after `uv sync` installs the development group.
- `pnpm dev`: build the worker and launch the desktop in development mode.
- `pnpm contracts:generate`: regenerate OpenAPI and TypeScript API definitions.
- `pnpm package:mac`: prepare the embedded Python runtime, build the workspace, create the unsigned Apple Silicon DMG, and verify its runtime layout.

Selectable-text PDF/DOCX résumé import and provenance review are implemented. OCR, document generation, job-requirement extraction, synthetic form filling, production ATS adapters, Gmail, and distribution hardening remain future milestones. Do not describe the current build as a complete auto-apply product.
