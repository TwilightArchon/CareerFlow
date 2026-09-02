# Feature: Desktop Control Center

Status: foundation implemented  
Owner: `apps/desktop`  
Last updated: 2026-08-24

## Purpose

Provide one independent desktop UI for first-time setup, starting an application from a URL, watching automation, resolving interventions, and reviewing application results and statistics.

## User flow

1. The user completes onboarding and chooses profile, browser, email, approval, and submission settings.
2. The user pastes a job URL, reviews the extracted job summary, and starts an authorized run.
3. The UI displays the current workflow state, active browser step, elapsed time, and any requested intervention.
4. The user may pause, resume, cancel, correct data, or open the controlled browser at any time.
5. The completed or failed run appears in application history with evidence and reason codes.

## Responsibilities

- Own navigation, settings, run commands, live status, interventions, history, and statistics.
- Restore UI state after reload without losing the underlying workflow.
- Clearly distinguish proposed, executing, paused, submitted, failed, cancelled, and uncertain states.
- Never hide browser automation or treat closing the UI as permission to submit.

## Inputs and outputs

Input includes user settings, job URLs, corrections, authorization scopes, and intervention responses. Output includes versioned run commands and UI views derived from canonical workflow records. The UI is not the source of truth for workflow state.

## States and failure handling

Desktop process restart must reconnect to active runs. Invalid URLs, unavailable services, browser disconnects, and stale intervention requests must produce actionable recovery messages. Pause and cancel must be idempotent.

## Policy, security, and privacy

Sensitive values are masked by default. The renderer cannot directly read secrets from the keychain or execute arbitrary browser actions. Destructive profile deletion and submission-mode changes require explicit confirmation.

## Acceptance criteria

- [ ] A new user can configure the MVP without editing a file or using a terminal.
- [ ] A run can be started, observed, paused, resumed, and cancelled from the desktop UI.
- [x] The UI recovers after reload and displays the canonical state. (Verified in the packaged 0.1.3 app with a persisted Workday run across two launches.)
- [ ] Success, failure, uncertainty, and human-required states are visually distinct and accessible.

## Tests and evaluations

Component tests cover state rendering and guarded actions. End-to-end tests cover onboarding, run control, reconnection, intervention, cancellation, and history navigation.

## Current implementation

The sandboxed React control center displays local service health, accepts and validates a job URL, captures per-run submit authorization, creates a durable run, and restores active queue cards from SQLite after relaunch. The Applications navigation now opens a durable run-history view showing URL, current state, recent activity, and submission-authorization status. The UI refreshes the canonical state while open instead of relying on one-session React memory. Labels explicitly describe the current navigation-only foundation and disable unfinished navigation items.

Profile & Evidence navigation now provides first-time manual onboarding and editing for the encrypted candidate profile. It also accepts a local PDF or DOCX résumé, shows encrypted source-document status, lists extracted page/section provenance, and lets the user explicitly verify individual evidence items. Image-only PDFs show an OCR-needed state without being misrepresented as parsed. The control center requires a verified saved profile before creating new application runs and explains the current navigation-only automation boundary.

The CommonJS preload exposes only health, run creation/listing, profile load/save, résumé import, and evidence verification and is compatible with Electron's sandboxed renderer. The 0.1.5 package compiles internal runtime contracts, includes the browser worker and its dependencies inside the app archive, and launches an embedded Python 3.13 runtime without destination-machine package installation. Missing or failed child processes become controlled startup failures instead of uncaught Electron exceptions. Interventions, pause/resume/cancel, extracted job metadata, outcomes, filters, and statistics remain pending.
