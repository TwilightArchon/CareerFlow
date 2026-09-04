# Feature: Desktop Control Center

Status: profile, job review, grounded preparation, navigation, safe autofill, and tracking implemented
Owner: `apps/desktop`  
Last updated: 2026-09-03

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

Profile & Evidence navigation now supports résumé-first or manual onboarding and editing for the encrypted candidate profile. The file picker accepts a local PDF or DOCX and a local deterministic preview fills only empty identity, contact, link, and education fields for review, both before and after profile creation. LinkedIn and GitHub URLs embedded behind clickable PDF labels are included without a model call. Preview and encrypted evidence import are separate actions for existing profiles, which permits re-extraction without duplicate document storage; every proposed field still requires an explicit profile save. Creating a new profile encrypts and imports the selected source document. The view shows encrypted source-document status, lists extracted page/section provenance, and lets the user explicitly verify individual evidence items. Image-only PDFs show an OCR-needed state without being misrepresented as parsed.

The control center accepts a public HTTP(S) job link independently of profile completion and displays a durable normalized job review with title, company, location, detected platform/confidence, extraction warnings, and required/preferred statements. With a verified profile, **Prepare grounded draft** requests a local, version-checked evidence plan and displays weighted coverage, supported/partial/gap counts, per-requirement explanations, exact matched statements, and source provenance. The UI states explicitly that this baseline uses zero AI tokens. Editing the URL or saving a new profile version clears the stale plan.

Opening the resolved posting in the visible browser is disabled until the user prepares a current plan. A `needs_evidence` plan directs the user to verify relevant résumé statements first; a reviewable plan enables explicit confirmation and run creation. Material editing, approval persistence, and generated-document preview remain pending.

The control center also exposes **Test profile autofill** after a verified profile and both local services are ready. It creates a durable synthetic run, opens the app-owned Safe Autofill Lab in the visible browser, explains the no-employer/no-submit boundary, and lets the normal two-second durable-run refresh show its progress to `Needs attention`. Ordinary approved fields are highlighted in the browser; contact and legal fields remain blank for review.

Active queue and Applications cards now provide Pause/Resume and Cancel controls. Pause preserves a durable pre-pause checkpoint while leaving the visible browser open. Resume requires the browser worker and restores the checkpointed workflow state; synthetic runs are safely rescanned. Cancel asks for confirmation, records a terminal transition and cancellation outcome, and removes the run from the active queue.

In Applications, **View field decisions** loads durable explanations for one run through an allowlisted IPC/API path. The expanded card shows which canonical fields were filled or held, the deterministic mapping rationale, and the policy result. Candidate values are intentionally absent from this response and UI.

Each application card also lets the user explicitly confirm or correct its outcome using a constrained outcome and reason taxonomy. Corrections append revisions instead of deleting prior records. The page shows locally reconciled tracked/pending/submitted/resolution totals and filters by outcome and platform. Recording an outcome does not pretend that CareerFlow performed a real submission; a submitted outcome is labeled as user-confirmed evidence.

The CommonJS preload exposes only health, run creation/listing/control, outcome/statistics operations, the bounded synthetic-demo command, job ingestion, version-checked material preparation, profile load/save, local résumé preview/import, and evidence verification and is compatible with Electron's sandboxed renderer. The 0.1.10 package compiles internal runtime contracts, includes the browser worker and its dependencies inside the app archive, and launches an embedded Python 3.13 runtime without destination-machine package installation. Missing or failed child processes become controlled startup failures instead of uncaught Electron exceptions. Real ATS field correction, dynamic-page extraction, automated outcome evidence, policy-generated interventions, and automatic crash recovery remain pending.
