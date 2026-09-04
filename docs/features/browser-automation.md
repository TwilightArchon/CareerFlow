# Feature: Visible Browser Automation

Status: controlled synthetic scan/fill implemented
Owner: `packages/browser-worker`  
Last updated: 2026-09-03

## Purpose

Operate applicant-facing websites inside a visible, dedicated browser profile while keeping the user able to observe, pause, correct, and resume the run.

## User flow

The worker opens the job application, uses an adapter or semantic fallback, fills permitted fields, uploads approved documents, navigates pages, surfaces validation errors, and captures confirmation evidence. The user can bring the browser forward and take control at any time.

## Responsibilities

- Manage a persistent user-specific browser profile, sessions, tabs, downloads, and uploads.
- Execute only typed browser actions approved by workflow policy.
- Capture relevant DOM/accessibility context, screenshots, validation messages, and page transitions.
- Detect navigation loops, unexpected dialogs, session expiry, worker crashes, and manual user edits.
- Never bypass CAPTCHA, 2FA, bot detection, or access controls.

## Inputs and outputs

Inputs are authorized action plans, adapter selection, field values, artifact references, and workflow identifiers. Outputs are action results, observed fields, validation errors, page state hashes, screenshots, confirmation evidence, and intervention requests.

## States and failure handling

Actions are idempotent where possible. Retried fills must compare existing values before typing; uploads and submissions require stronger duplicate protection. A heartbeat and checkpoint allow worker restart without repeating irreversible steps.

## Policy, security, and privacy

The browser worker cannot access raw secrets except through narrowly scoped keychain operations. Web content is untrusted. Downloads, popups, deep links, and cross-origin navigation are validated before execution. Screenshots and traces follow redaction and retention policy.

## Acceptance criteria

- [ ] The browser remains visible and automation can be paused or cancelled.
- [ ] Restart recovery does not duplicate completed submissions or account creation.
- [ ] Every action is tied to a run, step, policy decision, and observable result.
- [ ] Human-only challenges generate interventions instead of bypass attempts.

## Tests and evaluations

Use local multi-page fixtures for navigation, upload, validation, popup, session expiry, manual edits, crash recovery, duplicate prevention, and CAPTCHA detection. Run end-to-end tests only against authorized test environments.

## Current implementation

The supervised worker authenticates to the local WebSocket, propagates W3C trace context, maintains heartbeats, lazily launches a visible Playwright-controlled Google Chrome profile, navigates on typed commands, rejects obvious or DNS-resolved private-network destinations, and reports a page-state fingerprint that includes hashed form state.

The app-owned Safe Autofill Lab is fulfilled entirely inside the browser worker at a reserved `.invalid` URL, contains no network dependencies or submit action, and exposes 12 conventional identity, contact, link, education, and legal controls. The worker scans labels, types, required state, autocomplete metadata, options, and deterministic sensitivity. Python remaps canonical sensitivity independently, applies policy, and returns only approved values. Before filling, the worker compares the current page-state hash with the scan hash; changed pages fail closed. Approved controls are filled idempotently and visually highlighted. Contact and legal controls remain blank and move the durable run to `awaiting_human`.

The worker maintains per-run pause/cancel gates. Typed pause leaves the visible page open but rejects subsequent action commands, resume removes only a non-cancelled pause gate, and cancel permanently blocks that run ID for the worker lifetime. The service also rejects late results against paused, cancelled, or outcome-complete runs, so browser acknowledgements cannot silently undo user control.

The normal suite verifies fixture isolation, sensitivity classification, contracts, mapping, policy, control gates, checkpoints, idempotency, and workflow history. `pnpm browser:test:integration` opens real visible Google Chrome and verifies scan, fill, state change, and stale-plan rejection. Real ATS inspection/filling, uploads, automatic restart recovery, and confirmation capture remain pending.
