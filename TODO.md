# CareerFlow Implementation Roadmap

This is the execution checklist. Feature behavior and acceptance criteria live in `docs/features/`; this file tracks sequencing and verified completion.

## Phase 0 — Decisions and foundations

- [x] Define the desktop-first product and automation boundaries.
- [x] Create canonical agent instructions and documentation synchronization rules.
- [x] Create a documentation index and one specification per planned capability.
- [x] Review and accept ADR 0001 for the desktop architecture and technology stack.
- [x] Define repository layout, package manager, runtime versions, and local development commands.
- [x] Create a threat model covering credentials, PII, browser sessions, email access, model providers, and stored artifacts.
- [x] Define the canonical candidate, job, form-field, workflow, evidence, and application schemas.

Exit criterion: the architecture, trust boundaries, schemas, and build conventions are explicit enough to scaffold without unresolved high-cost decisions.

## Phase 1 — Local vertical slice

- [x] Scaffold the Electron + React + TypeScript desktop application.
- [x] Scaffold the Python FastAPI workflow and AI service.
- [x] Add local development startup, lint, type-check, test, and packaging commands. (Desktop launch, authenticated process handshake, production build, embedded Python runtime, unsigned DMG build, disk-image verification, compiled workspace-runtime and sandboxed preload verification, and isolated installed-app launch regression coverage completed on Apple Silicon.)
- [x] Implement encrypted local profile storage backed by the operating-system keychain. (Immutable profile versions, verified manual-entry facts, AES-256-GCM ciphertext, Keychain key reference, authenticated APIs, stale-write protection, and fail-closed key handling implemented and tested.)
- [x] Import a resume and create the candidate evidence ledger with provenance. (Selectable-text PDF and DOCX parsing, encrypted original artifacts, page/section spans, duplicate detection, image-only PDF status, immutable profile integration, and explicit evidence verification are implemented and tested.)
- [ ] Accept a public job URL and extract normalized job requirements.
- [ ] Map requirements to candidate evidence and generate a grounded resume draft.
- [ ] Launch a visible persistent browser and fill a controlled local test form. (Dedicated visible-browser navigation implemented; controlled form scan/fill pending.)
- [ ] Save the run, field-level explanations, and outcome to the dashboard. (Durable run restoration and the initial Applications history view are implemented; extracted job metadata, field explanations, outcomes, and statistics remain.)

Exit criterion: one local test job flows from pasted URL to prepared application and recorded outcome without unsupported claims.

## Phase 2 — Reliable application workflow

- [ ] Implement the durable application state machine, checkpoints, resume, cancel, retries, timeouts, and idempotency. (Validated transitions, append-only events, authorization, and idempotency implemented; checkpoints/recovery controls pending.)
- [ ] Implement field confidence and action policies. (Initial sensitivity/source/confidence policy and tests implemented; complete field taxonomy pending.)
- [ ] Add the human-intervention inbox with clear reasons and resume controls.
- [ ] Add document upload, validation-error handling, multi-page navigation, and review-page verification.
- [ ] Add user-authorized auto-submit mode with policy gates and confirmation capture.
- [ ] Add application history, success/failure taxonomy, filters, and statistics. (Durable URL/state/activity/authorization history is implemented; outcomes, failure taxonomy, filters, and statistics remain.)
- [ ] Add trace correlation across UI, browser, workflow, and model calls. (W3C propagation and process instrumentation implemented; end-to-end trace verification pending.)

Exit criterion: interrupted runs recover safely, sensitive actions pause correctly, and every automated action is explainable.

## Phase 3 — ATS coverage

- [ ] Implement and fixture-test the Greenhouse adapter.
- [ ] Implement and fixture-test the Lever adapter.
- [ ] Implement and fixture-test the Workday adapter.
- [ ] Implement the generic semantic fallback using DOM and accessibility signals.
- [ ] Add adapter detection, capability reporting, versioning, and graceful degradation.
- [ ] Add regression fixtures for layout changes and known failures.

Exit criterion: the supported-platform matrix and accuracy metrics meet the thresholds in each feature specification.

## Phase 4 — Registration and email verification

- [ ] Add account-registration plans using user-configured identity and credential policies.
- [ ] Integrate Gmail through least-privilege OAuth for verification-link retrieval.
- [ ] Add safe handling for existing accounts, password rules, duplicate accounts, expired links, and logout/session recovery.
- [ ] Keep CAPTCHA, 2FA, mailbox consent, and ambiguous verification behind human intervention.

Exit criterion: supported registration flows can resume after a human checkpoint without exposing credentials or email content.

## Phase 5 — Evaluation, operations, and portfolio proof

- [ ] Build golden datasets for extraction, evidence mapping, field mapping, and answer policy.
- [ ] Add deterministic, model-based, adversarial, and end-to-end evaluations.
- [ ] Add CI quality gates, trace replay, failure dashboards, latency/cost metrics, and PII-safe logging checks.
- [ ] Measure time saved, completion rate, intervention rate, field accuracy, unsupported-claim count, and recovery rate.
- [ ] Record an architecture walkthrough and end-to-end demo using synthetic candidate data.
- [ ] Publish a portfolio case study with metrics, tradeoffs, incident examples, and lessons learned.

Exit criterion: CareerFlow demonstrates production-oriented agent orchestration, evaluation, observability, security, and human-controlled automation with measurable results.

## Phase 6 — Multi-user scale

- [ ] Separate local device execution from the multi-tenant control plane.
- [ ] Add authentication, tenancy, authorization, quotas, billing-ready usage accounting, and deletion/export workflows.
- [ ] Move shared metadata to managed PostgreSQL and background work to durable infrastructure.
- [ ] Add signed desktop updates, release channels, migration strategy, and support diagnostics.

Exit criterion: multiple users can operate isolated accounts without sharing credentials, browser sessions, or private application data.
