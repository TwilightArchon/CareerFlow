# CareerFlow Problem and Solution Log

Last updated: 2026-09-03

## Purpose

This is the durable record of significant problems encountered while developing, packaging, testing, or operating CareerFlow. It exists to prevent repeated investigation and to preserve the evidence behind each solution.

Add an entry when a problem:

- affects users, releases, security, data integrity, or developer setup;
- takes meaningful investigation to diagnose;
- reveals a missing test, packaging check, or architectural constraint; or
- remains unresolved and could affect later work.

Never include credentials, tokens, private résumé content, email content, or unnecessary personal data. Link to sanitized fixtures or tests instead.

## Entry format

Each entry should include:

- **Status:** open, mitigated, or resolved.
- **Area:** affected component or workflow.
- **Symptom:** what was observed.
- **Root cause:** the verified reason, not an initial guess.
- **Resolution:** the implemented correction or current mitigation.
- **Verification:** commands, tests, or runtime evidence proving the result.
- **Prevention:** the regression guard or follow-up work.

## Resolved problems

### CF-017 — Visible Chrome integration could not launch inside the restricted test sandbox

- **Status:** resolved as a test-environment issue
- **Area:** Playwright visible-browser integration verification
- **Symptom:** The opt-in Safe Autofill Lab integration test launched Google Chrome, but Chrome aborted while its crash handler attempted to access OS-managed application-support services and files.
- **Root cause:** The restricted command sandbox allowed repository writes but did not grant the macOS process and application-support permissions required by a visible GUI browser.
- **Resolution:** Run the same narrowly scoped integration command with approved GUI access; no application code or browser security boundary was weakened.
- **Verification:** `pnpm browser:test:integration` opened visible Google Chrome, scanned all 12 controls, filled an approved field, detected the form-state change, rejected reuse of the stale scan hash, and closed cleanly.
- **Prevention:** Keep the visible-browser test opt-in and separate from headless CI. Run it in a macOS release environment with Google Chrome and GUI permission before accepting a DMG.

### CF-016 — Clickable LinkedIn and GitHub labels were not extracted from PDFs

- **Status:** resolved
- **Area:** deterministic résumé parsing and first-time profile preview
- **Symptom:** A selectable-text résumé displayed clickable LinkedIn and GitHub labels, but CareerFlow did not suggest either profile URL.
- **Root cause:** PDF text extraction reads the visible label from a page content stream but does not return the destination stored separately in the page's `/Link` annotation and `/URI` action.
- **Resolution:** Inspect a bounded number of page annotations locally and add recognized profile destinations to the parsed evidence stream with page and `hyperlink` provenance. Accept only HTTP(S) LinkedIn `/in/…` links and single-segment GitHub profile links; normalize to HTTPS and discard repository links, unrelated hosts, queries, fragments, credentials, non-standard ports, and non-HTTP(S) schemes. Keep the token-free field-preview action available for existing profiles so the user can recover new suggestions without attempting a duplicate evidence import; only empty fields are filled and the user must save them explicitly.
- **Verification:** A synthetic regression PDF recovers both profile links while excluding a GitHub repository URL and a script-scheme URL. A privacy-safe local check of the supplied two-page résumé reports both profile fields found on page 1. A desktop regression proves suggestions fill an empty link without replacing an existing verified link. All 24 Python and 11 TypeScript tests, repository checks, strict mypy, production build, packaged-runtime verification, and DMG verification pass.
- **Prevention:** The annotation regression fixture and URL-boundary assertions run with the normal Python test suite; annotation inspection and evidence output remain explicitly bounded.

### CF-015 — Workday requirements were missed when metadata flattened the description

- **Status:** resolved
- **Area:** deterministic job ingestion
- **Symptom:** The supplied public Workday posting produced the correct title, company, location, and platform but zero requirements, leaving the review in `needs_review`.
- **Root cause:** Workday exposed the full description as one flattened JSON-LD/Open Graph string without list or heading line breaks. The first parser pass intentionally rejected an oversized one-line candidate, so the embedded `Your Background` section was not segmented.
- **Resolution:** Add a bounded second deterministic pass that isolates known requirement headings, stops before EEO/benefits/company sections, and separates sentence and common qualification starts while retaining exact source offsets.
- **Verification:** A sanitized flattened-Workday regression fixture recovers four requirements with exact source spans. The supplied posting recovers six requirements, reports Workday at 0.99 confidence, and completes without warnings or a model call.
- **Prevention:** Both structured HTML-list and flattened Workday representations are regression tested. Ingestion remains `needs_review` when neither deterministic pass finds requirements.

### CF-014 — Résumé import was disabled before manual profile creation

- **Status:** resolved
- **Area:** first-time profile onboarding and résumé extraction
- **Symptom:** The résumé picker and import button were disabled for a new user, forcing manual profile creation before CareerFlow could read a résumé.
- **Root cause:** The renderer gated both controls on an existing `CandidateProfileSnapshot`, and the only résumé API required an existing immutable profile version because it immediately persisted encrypted evidence.
- **Resolution:** Add a separate authenticated, non-persistent preview path that parses the selected PDF/DOCX in memory and suggests supported profile fields with confidence and source spans. The renderer fills only empty fields for review. After the user saves the required identity fields, the existing import path encrypts the original and attaches its evidence to the new profile version.
- **Verification:** The API regression test extracts ten supported fields before profile creation and confirms the profile remains absent. All 18 Python tests, nine TypeScript tests, formatting, Ruff, TypeScript checks, strict mypy, generated-contract validation, and the production build pass.
- **Prevention:** Shared runtime schemas cover preview output, and onboarding copy explicitly distinguishes local suggestions from verified saved facts. Preview parsing makes no model or network request and records only count/status telemetry.

### CF-001 — Installed DMG crashed while loading TypeScript from `node_modules`

- **Status:** resolved in 0.1.1
- **Area:** Electron packaging and shared contracts
- **Symptom:** Opening the installed 0.1.0 application produced `ERR_UNSUPPORTED_NODE_MODULES_TYPE_STRIPPING` for `@careerflow/contracts/src/index.ts` in `app.asar`.
- **Root cause:** The shared contracts package exported its TypeScript source, and Electron Vite externalized that workspace dependency. Development mode transformed the source, but packaged Node attempted to execute it directly from `node_modules`.
- **Resolution:** The contracts package now emits JavaScript, its runtime export targets `dist/index.js`, and the Electron main build bundles the internal contracts package.
- **Verification:** Production build passed; the packaged archive contains compiled contracts; a clean packaged launch reached FastAPI startup and browser-worker connection without a JavaScript exception.
- **Prevention:** `scripts/verify-packaged-app.mjs` rejects a package whose main bundle still imports the workspace contracts package at runtime or whose compiled contract entry is missing.

### CF-002 — Packaged browser worker lacked resolvable runtime dependencies

- **Status:** resolved in 0.1.1
- **Area:** Playwright browser-worker packaging
- **Symptom:** Inspection of the 0.1.0 archive showed that the copied worker bundle still imported `@careerflow/contracts`, `playwright-core`, and `ws`, while the copied resource directory had no corresponding `node_modules` tree.
- **Root cause:** The browser worker was copied as an isolated `extraResource` even though its build externalized Node dependencies.
- **Resolution:** The worker is now a desktop runtime workspace dependency and is launched from inside `app.asar`, where Electron Builder packages its dependency graph.
- **Verification:** The packaged-runtime verifier confirmed the worker entry, Playwright, WebSocket, and compiled contracts. The clean packaged launch established the authenticated browser-worker WebSocket.
- **Prevention:** Release-layout verification checks every required worker runtime entry before accepting a DMG.

### CF-003 — First installed launch depended on `uv` and stalled during Python setup

- **Status:** resolved in 0.1.1
- **Area:** packaged Python service
- **Symptom:** After fixing the JavaScript crash, a clean packaged launch attempted to create a Python environment and download dependencies. It exceeded the readiness timeout and could also fail when Finder did not expose the shell path containing `uv`.
- **Root cause:** The destination application launched `uv run` and treated environment creation as first-launch work. That coupled app startup to shell configuration, package-server availability, and download speed.
- **Resolution:** The DMG now embeds relocatable CPython 3.13 and the verified Python runtime dependencies. Electron launches the embedded interpreter directly with the packaged agent source.
- **Verification:** A launch using an empty isolated user-data directory reached `Application startup complete` and connected the browser worker without `uv`, system Python, or dependency downloads.
- **Prevention:** `pnpm package:mac` prepares the embedded runtime, and the packaged-runtime verifier rejects an app that lacks the interpreter. The architectural decision is recorded in ADR 0003.

### CF-004 — DMG creation failed with `getaddrinfo ENOTFOUND github.com`

- **Status:** resolved as a build-environment issue
- **Area:** Electron Builder
- **Symptom:** Electron Builder reached the macOS packaging step and failed while fetching the Electron distribution from GitHub.
- **Root cause:** The restricted build environment could not access the network, and the required Electron archive was not available in its accessible cache.
- **Resolution:** The packaging command was rerun with approved network access. The artifact was downloaded and the build completed.
- **Verification:** `pnpm package:mac`, packaged-runtime verification, and `hdiutil verify` all passed.
- **Prevention:** Build environments must either permit the pinned Electron download or preload the Electron Builder cache. This condition is not an application runtime failure.

### CF-005 — Generated contracts and edited source failed formatting validation

- **Status:** resolved
- **Area:** repository quality checks
- **Symptom:** `pnpm check` reported formatting differences in the supervisor, generated OpenAPI JSON, and generated TypeScript contracts.
- **Root cause:** Contract regeneration and the packaging fix produced files that had not yet passed through the repository formatter.
- **Resolution:** Ran `pnpm format`, then reran the full check.
- **Verification:** `pnpm check` passed, including Prettier, TypeScript checking, and Ruff.
- **Prevention:** Run formatting after contract generation and before the release verification suite.

### CF-007 — Packaged UI remained at `0/2 services ready`

- **Status:** resolved in 0.1.2
- **Area:** Electron preload bridge and desktop health display
- **Symptom:** The packaged application stayed at `0/2 services ready`; Database and Browser worker both displayed `Starting`, and Review job remained disabled even though the Python service and browser worker processes were running.
- **Root cause:** Electron's sandboxed preload environment does not support ESM imports. The build emitted `out/preload/index.mjs`, which failed with `SyntaxError: Cannot use import statement outside a module` before it could expose `window.careerflow`. Renderer health requests therefore failed and the UI displayed its degraded fallback state.
- **Resolution:** The preload is now bundled as CommonJS at `out/preload/index.cjs`, while keeping sandboxing, context isolation, and Node integration restrictions unchanged. Electron main loads that CommonJS bridge.
- **Verification:** The production build emits `index.cjs`; the package verifier requires the bridge and rejects `index.mjs`. A clean 0.1.2 packaged launch using an isolated user-data directory displayed `Ready`, `2/2 services ready`, `Database Connected`, and `Browser worker Connected`; the Review job button was enabled.
- **Prevention:** `scripts/verify-packaged-app.mjs` validates the preload format and confirms that the packaged bridge exposes the allowlisted renderer API.

### CF-008 — Application queue disappeared after relaunch

- **Status:** resolved in 0.1.3
- **Area:** desktop queue restoration and application tracking
- **Symptom:** A created run appeared in the control-center queue and opened its browser, but the queue was empty after CareerFlow was closed and reopened even though the SQLite record still existed.
- **Root cause:** The renderer appended new cards only to one-session React state. The local API exposed run creation and per-run events but had no authenticated run-list endpoint, so startup had no supported path to rebuild the UI from durable workflow state.
- **Resolution:** SQLite now returns runs ordered by recent activity through an authenticated typed endpoint. Electron validates the projection against shared runtime schemas, and the renderer restores and refreshes the active queue and Applications history after the database becomes ready. SQLite's timezone-naive returned timestamps are explicitly interpreted as UTC before serialization.
- **Verification:** API coverage verifies ordering, current state, URLs, and UTC timestamp markers. The packaged 0.1.3 app restored the existing Hitachi Workday run as `Browser opened`, showed it in Applications with the correct local activity time, closed cleanly, and restored the same run on a second launch. Formatting, TypeScript, Ruff, 15 automated tests, package-layout verification, and DMG checksum verification passed.
- **Prevention:** The durable renderer projection has shared runtime validation and API regression coverage. The UI delays its first history read until database readiness, avoiding a startup race, and never clears previously loaded durable data after a transient read failure.

### CF-006 — Strict Python `mypy` validation reports five errors

- **Status:** resolved in 0.1.5
- **Area:** Python static typing
- **Symptom:** Direct strict checking reports five errors across contracts, workflow, telemetry, API trace context, and the OpenAI reasoning argument.
- **Root cause:** Several annotations are narrower than the inferred or SDK-provided types, including a nullable SQL aggregate and updated third-party protocol signatures.
- **Resolution:** Narrowed schema and reasoning-effort literals, used the OpenAI SDK's typed reasoning request, matched the OpenTelemetry exporter protocol, preserved SQL aggregate nullability, validated stored URLs as `AnyHttpUrl`, constructed typed trace context, and narrowed résumé media types after validation. The command now uses the already-synced development environment rather than attempting an unnecessary network sync.
- **Verification:** `pnpm python:typecheck` reports no issues across all 14 Python source files. The full Ruff, TypeScript, and 25-test suite also passes.
- **Prevention:** Strict mypy remains a documented release command and must pass without suppressing real incompatibilities.

### CF-009 — Embedded-runtime refresh rejected the `uv pip sync` arguments

- **Status:** resolved in 0.1.5
- **Area:** packaged Python dependency refresh
- **Symptom:** Adding PDF/DOCX libraries required refreshing the existing embedded runtime, but `pnpm runtime:prepare` stopped with `unexpected argument '--requirements' found`.
- **Root cause:** The runtime script used an older `uv pip sync --requirements FILE` form. The installed pinned tool accepts the requirements path as a positional argument.
- **Resolution:** Pass the exported locked requirements file positionally. The script now refreshes an existing valid interpreter when runtime dependencies change and still rejects structurally incomplete runtimes.
- **Verification:** `pnpm runtime:prepare` imports `docx` and `pypdf` from the embedded CPython runtime, and packaged-runtime verification executes the same import gate inside the built application.
- **Prevention:** The DMG build always runs runtime preparation, and `scripts/verify-packaged-app.mjs` rejects missing document-parser dependencies.

### CF-010 — GitHub Actions could not locate `pnpm`

- **Status:** resolved
- **Area:** continuous integration toolchain setup
- **Symptom:** The `verify` job stopped before dependency installation with `Unable to locate executable file: pnpm` and warned that `actions/checkout@v4` and `actions/setup-node@v4` targeted deprecated Node.js 20.
- **Root cause:** `actions/setup-node` was configured with `cache: pnpm` before `pnpm/action-setup` added the pinned pnpm executable to `PATH`. setup-node queries the pnpm store during its cache setup, so the workflow failed immediately. The v4 official actions also used the deprecated Node.js 20 action runtime.
- **Resolution:** Run `pnpm/action-setup` before `actions/setup-node`, retain the repository's pinned pnpm 10.15.1 and Node.js 24 toolchain, upgrade checkout and setup-node to their Node-24-backed v6 majors, make the pnpm lockfile cache input explicit, and print all resolved tool versions before installation.
- **Verification:** `pnpm ci:check` validates the action order, maintained action majors, Node version file, and frozen pnpm install. `pnpm check` and the complete local test suite pass. GitHub Actions run `32899076422` completed checkout, pnpm setup, setup-node, setup-uv, toolchain verification, and both frozen dependency installs; it then exposed the independent generated-contract problem recorded as CF-011.
- **Prevention:** `scripts/verify-ci-workflow.mjs` runs inside `pnpm check` and fails locally if pnpm setup moves behind setup-node or required toolchain and lockfile pins disappear.

### CF-011 — Clean CI regenerated differently formatted contracts

- **Status:** resolved
- **Area:** generated OpenAPI and TypeScript contracts
- **Symptom:** After the pnpm setup fix, GitHub Actions regenerated `packages/contracts/openapi.json` and `packages/contracts/src/generated.ts`, then failed the clean-tree diff gate with formatting-only changes. The run also showed that `astral-sh/setup-uv@v6` still targeted the deprecated Node.js 20 action runtime.
- **Root cause:** `contracts:generate` produced raw generator formatting, while the committed artifacts had subsequently been formatted by Prettier. CI compared the files before `pnpm check` could format or report them. Separately, setup-uv remained on its older Node-20-backed major.
- **Resolution:** Make contract generation format both generated artifacts as part of the same command, so generation is deterministic at its public boundary. Upgrade setup-uv to a Node-24-backed release and extend the CI configuration guard to reject the deprecated action revision.
- **Verification:** Two consecutive `pnpm contracts:generate` runs leave both committed contract files unchanged. `pnpm ci:check`, `pnpm check`, the complete test suite, and the production build pass locally. GitHub Actions run `32899466395` also passed the clean generated-contract diff, all checks, all tests, and the production build.
- **Prevention:** Contract generation owns output formatting, CI immediately checks for a clean generated diff, and the local CI guard validates every action involved in the pinned toolchain.

### CF-012 — GitHub could not resolve the advertised `setup-uv@v9` tag

- **Status:** resolved
- **Area:** GitHub Actions dependency resolution
- **Symptom:** GitHub Actions run `32899339216` failed during job preparation with `Unable to resolve action astral-sh/setup-uv@v9` before any repository command executed.
- **Root cause:** The setup-uv repository's development README advertised v9, but GitHub could not resolve a published `v9` tag when the workflow ran. A moving major inferred from development documentation was therefore not a valid hosted action reference.
- **Resolution:** Pin setup-uv to Astral's officially documented immutable v8.1.0 commit, `08807647e7069bb48b6ef5acd8ec9567f424441b`, while continuing to pin the installed uv executable to 0.12.5.
- **Verification:** `pnpm ci:check` requires the exact reviewed action revision and all local quality gates pass. GitHub Actions run `32899466395` resolved the immutable action revision, completed without the Node.js 20 warning, and passed in 1 minute 7 seconds.
- **Prevention:** Third-party CI actions should use a published immutable commit SHA from the vendor's official integration guide rather than a moving major observed only on a development branch.

### CF-013 — Public Git history contained candidate-specific metadata

- **Status:** resolved on 2026-09-02
- **Area:** repository privacy and Git metadata
- **Symptom:** A public planning brief included résumé-derived personal details, and commit author metadata used a personal email address. No credential, token, private document, application record, or local artifact was exposed.
- **Root cause:** An internal career-planning brief was published without a public-document sanitization pass, and the repository inherited a personal Git author email.
- **Resolution:** Rewrite the brief as candidate-agnostic product rationale, configure the repository to use the account's GitHub noreply identity, replace `main` with one clean root commit, and force-push with a lease after local privacy verification.
- **Verification:** Local and remote `main` contain one parentless root commit authored with the GitHub noreply identity. Current-tree scans find none of the removed personal markers, credential signatures, private documents, application data, databases, browser profiles, or build artifacts. Formatting, repository checks, and all 25 automated tests pass.
- **Prevention:** `SECURITY.md` now requires public-safe planning documents, synthetic fixtures, and noreply commit metadata. Repository exposure reviews must inspect commit metadata and reachable history in addition to current files.

## Maintenance rule

When diagnosing a known symptom, read this file before changing code. When a significant problem is confirmed, add or update its entry in the same change as the fix. A resolved entry must include verification evidence and must never be deleted merely because the implementation later changes.
