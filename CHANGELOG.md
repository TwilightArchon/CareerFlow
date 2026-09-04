# Changelog

All notable CareerFlow changes are documented here.

## 0.1.9 — 2026-09-03

### Added

- Added append-only, user-confirmed application outcomes with constrained submitted, failed, cancelled, abandoned, and uncertain states.
- Added stable outcome reason codes, idempotent repeat handling, revision linkage, and non-PII confirmation fingerprints for user-confirmed submissions.
- Added durable outcome audit retrieval, latest-outcome run projections, outcome/platform dashboard filters, and aggregate tracked/pending/submitted/resolution statistics.
- Added OpenTelemetry outcome-write spans and bounded outcome/reason metrics.

### Security

- Outcome corrections accept no free-form answer content, and submitted status requires an explicit user confirmation flag.

## 0.1.8 — 2026-09-03

### Added

- Added an app-owned Safe Autofill Lab that opens in the visible persistent browser, scans 12 conventional controls, and fills policy-approved verified profile facts without contacting an employer.
- Added deterministic label/autocomplete mapping, canonical sensitivity enforcement, typed scan/fill messages, evidence-linked fill plans, and redacted workflow counts.
- Added durable field-level decision records and an Applications detail view showing canonical mapping, confidence policy outcome, and rationale without exposing candidate values.
- Added redacted OpenTelemetry browser-action counts, latency, and scan/fill cardinalities.
- Added an opt-in real-Chrome integration test for visible form opening, scanning, filling, and stale-page rejection.

### Security

- Contact and legal fields remain blank for human review, the lab has no submit action, and a page-state check rejects a fill plan if the form changes after inspection.

## 0.1.7 — 2026-09-03

### Added

- Added deterministic requirement-to-evidence mapping with supported, partial, and unsupported classifications, confidence, matched terms, and exact evidence provenance.
- Added a review-only grounded résumé draft that selects verbatim verified evidence without an OpenAI call or token use.
- Added an authenticated, profile-version-checked material-preparation API and desktop review UI with coverage and gap summaries.

### Changed

- Opening the visible application browser now requires preparing a current grounded material plan; profiles without verified relevant evidence receive an actionable verification prompt.

## 0.1.6 — 2026-09-02

### Added

- Added résumé-first onboarding with local deterministic suggestions for common identity, contact, link, and education fields.
- Added token-free extraction of LinkedIn and GitHub profile destinations stored in PDF hyperlink annotations, with page provenance and strict URL allowlisting.
- Added an authenticated, non-persistent preview API and source-span/confidence contracts without OpenAI calls or token use.
- Added regression coverage proving preview works before profile creation and does not persist a profile.
- Added guarded public job retrieval, JSON-LD/Open Graph normalization, deterministic requirement extraction, ATS hostname detection, versioned SQLite job records, and a desktop job-review card.
- Added normalized job title, company, and platform to durable application history rows.

### Changed

- The résumé picker is available before profile creation, fills only empty form fields, and imports the encrypted source document after the user reviews and saves the profile.
- Existing profiles can rerun token-free résumé suggestions without re-importing a duplicate document; extracted values still fill only empty fields and require a separate save.
- Pasting a job URL now reviews and persists extracted details before an application run is created or the visible browser opens.

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
