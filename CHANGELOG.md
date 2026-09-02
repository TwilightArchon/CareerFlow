# Changelog

All notable CareerFlow changes are documented here.

## 0.1.5 — 2026-08-24

### Added

- Added local selectable-text PDF and DOCX résumé import with deterministic page, paragraph, heading, and table-row provenance.
- Added AES-256-GCM encrypted source-document artifacts, duplicate-content detection, bounded parser limits, and retained `needs_ocr`/failure states.
- Added a desktop résumé picker, imported-document status, extracted-evidence review, and immutable verification updates.
- Added authenticated multipart import and evidence-verification APIs plus OpenTelemetry `document.parse` spans.
- Added regression fixtures for DOCX paragraphs/tables, selectable PDF text, image-only PDFs, encrypted plaintext absence, version preservation, duplicate imports, and API review flows.

### Changed

- Manual profile edits now preserve imported documents and evidence instead of rebuilding away source history.
- Verified the 0.1.4 Keychain-backed profile against the packaged app: encrypted save, plaintext absence, full restart, and decryption restoration all passed.

## 0.1.4 — 2026-08-23

### Added

- Added desktop candidate-profile onboarding for identity, contact, location, links, education, and optional explicit work-authorization answers.
- Added immutable candidate-profile versions encrypted with AES-256-GCM and a 256-bit key stored only in macOS Keychain.
- Added authenticated typed profile load/save APIs, stale-write protection, fail-closed missing-key handling, and verified-fact provenance.
- Added tests proving sensitive profile values do not occur in plaintext SQLite storage.

### Changed

- New application runs now reference the current saved profile ID and version instead of placeholder random profile identifiers.
- Opening a new application is disabled until the user completes the encrypted profile.

## 0.1.3 — 2026-08-23

### Added

- Added an authenticated durable run-list endpoint ordered by recent workflow activity.
- Restored active queue entries from SQLite after desktop relaunch and refreshed their canonical state while the app is open.
- Made Applications navigation functional with local URL, state, activity, and submission-authorization history.
- Added runtime validation and API regression coverage for the restored application projection.

### Changed

- Replaced the misleading `Review job` and `filling` UI language with navigation-only descriptions that match the implemented foundation.
- Disabled unfinished Profile, Interventions, and Settings navigation instead of presenting them as working controls.
- Preserved UTC semantics when SQLite timestamps are returned so activity displays in the user's correct local time.

## 0.1.2 — 2026-08-23

### Fixed

- Built the sandboxed Electron preload bridge as CommonJS so the packaged renderer can read service health and invoke run commands.
- Added a packaged-runtime regression check that requires the CommonJS preload and rejects the incompatible ESM preload.

## 0.1.1 — 2026-08-23

### Fixed

- Prevented packaged Electron startup from loading `@careerflow/contracts/src/index.ts` from `node_modules`.
- Emitted a compiled JavaScript runtime for shared contracts and bundled contracts into the Electron main process.
- Packaged the browser worker as a workspace runtime dependency with Playwright and WebSocket dependencies available inside the app archive.
- Embedded CPython 3.13 and the verified runtime dependencies so installed builds no longer require `uv`, Python, or first-launch package downloads.
- Converted missing or failed child processes into controlled startup failures instead of uncaught main-process errors.
- Added a packaged-runtime layout check to the DMG build.

## 0.1.0 — 2026-08-23

### Added

- Electron and React desktop control center with sandboxed preload APIs.
- Authenticated loopback FastAPI service and browser-worker WebSocket.
- Canonical Pydantic contracts, OpenAPI export, and generated TypeScript definitions.
- SQLite application runs and append-only idempotent workflow transitions.
- Per-run submission authorization gate and initial field-mapping policy.
- AES-256-GCM payload encryption, macOS Keychain wrapper, and recursive redaction.
- Visible Playwright-controlled persistent Chrome profile and guarded job navigation.
- OpenTelemetry instrumentation, local Collector/Jaeger configuration, and bounded redacted diagnostics.
- pnpm and uv lockfiles, CI workflow, tests, production builds, and unsigned Apple Silicon DMG packaging.

### Known limitations

- Profile import, DOCX/PDF generation, synthetic form filling, recovery checkpoints, Workday, Gmail, Greenhouse, Lever, semantic fallback, and complete history remain future milestones.
- The 0.1.0 unsigned prototype expects `uv`, Google Chrome, and first-launch network access on the destination Mac; this is fixed in 0.1.1.
