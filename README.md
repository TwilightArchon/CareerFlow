# CareerFlow

CareerFlow is a desktop-first, supervised job-application agent. A user pastes a job link, and CareerFlow prepares an evidence-grounded application, operates a visible browser, handles routine registration and form filling, pauses for human-only decisions, and records both successful and unsuccessful attempts for analysis.

## Implemented foundation

- Desktop and UI: Electron, React, TypeScript, Vite
- Browser automation: Playwright with a dedicated persistent browser profile
- AI and workflow service: Python 3.13, FastAPI, Pydantic, LangGraph, and the OpenAI Responses API boundary
- Data: local SQLite workflow records plus AES-256-GCM encrypted-payload support and macOS Keychain references
- Tracking: restored application history, append-only user-confirmed outcome revisions, stable reason codes, outcome/platform filters, and locally reconciled statistics
- Run control: durable pause checkpoints, checkpoint-backed resume, confirmed cancellation, stale-result protection, and independent browser-worker action gates
- Explainability: durable per-run field decisions show what was filled or held for review and why, without displaying saved candidate values
- Profile vault: token-free résumé-first profile suggestions, including PDF-embedded LinkedIn/GitHub profile links, plus verified facts in immutable AES-256-GCM encrypted versions with the key held in macOS Keychain
- Grounded preparation: local requirement-to-evidence matching, explicit coverage gaps, and a verbatim review draft sourced only from verified evidence
- Safe autofill lab: an app-owned visible-browser form that scans conventional controls, deterministically maps verified profile facts, fills only policy-approved ordinary fields, and stops without submission
- Job review: guarded public-page retrieval, deterministic structured-metadata and requirement extraction, platform detection, and versioned local records before browser navigation
- Résumé evidence: local selectable-text PDF and DOCX parsing, encrypted source artifacts, page/section provenance, and explicit evidence review
- Observability and quality: OpenTelemetry, bounded redacted diagnostics, pytest, Ruff, Vitest, and generated OpenAPI contracts
- Security: operating-system keychain, OAuth, encrypted local data, explicit policy and approval gates

Real ATS form filling, Workday automation, Gmail OAuth, résumé generation, and semantic fallback are not implemented yet. Image-only PDFs are retained securely but still require a future OCR step.

## Development requirements

- macOS 14+ on Apple Silicon
- Node.js 24 and pnpm 10.15.1
- Python 3.13 and uv
- Google Chrome for the current visible-browser development path

The installed DMG includes its own Python 3.13 runtime and Python packages. End users do not need Node.js, pnpm, Python, `uv`, or first-launch dependency downloads. Google Chrome is still required for visible browser automation.

## Development

```sh
pnpm install
uv sync --project services/agent
pnpm contracts:generate
pnpm check
pnpm python:typecheck
pnpm test
pnpm browser:test:integration
pnpm dev
```

Optional local traces are available after `pnpm telemetry:up`; open Jaeger at `http://127.0.0.1:16686` and set `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318` before starting CareerFlow. External telemetry is disabled by default.

`pnpm package:mac` prepares the embedded Python runtime, builds every workspace dependency, creates the unsigned Apple Silicon DMG, and verifies that the packaged app contains compiled contracts, the browser worker, Python, and their runtime dependencies. Preparing the runtime may need network access on a new development machine; opening the generated app does not.

## Start here

- Product definition: [`docs/PROJECT.md`](docs/PROJECT.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Documentation map: [`docs/INDEX.md`](docs/INDEX.md)
- Build roadmap: [`TODO.md`](TODO.md)
- Agent instructions: [`AGENTS.md`](AGENTS.md)
- Prototype history: [`CHANGELOG.md`](CHANGELOG.md)
- Problems and solutions: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

## Current status

Foundation, deterministic job review, encrypted résumé-evidence, grounded material preparation, supervised navigation, a controlled synthetic form-filling slice, durable run controls, and application tracking. The Safe Autofill Lab demonstrates visible scanning, canonical field mapping, policy-gated filling, stale-page protection, pause/resume/cancel, and a durable review-required state without contacting or submitting to an employer. Users can explicitly record and correct outcomes, filter history, and view statistics derived from local records. It is not ready for real automated applications.
