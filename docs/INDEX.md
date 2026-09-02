# CareerFlow Documentation Index

This file is the required starting point before changing CareerFlow. It maps each capability to its canonical specification.

## Core documents

- [`PROJECT.md`](PROJECT.md): product definition, users, scope, safety boundaries, and success measures.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): components, data flow, runtime boundaries, and proposed stack.
- [`THREAT_MODEL.md`](THREAT_MODEL.md): protected assets, trust boundaries, abuse cases, and required mitigations.
- [`DOCUMENTATION.md`](DOCUMENTATION.md): documentation conventions, agent-loading behavior, and future standard files.
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md): durable problem, root-cause, solution, verification, and prevention log.
- [`../TODO.md`](../TODO.md): ordered implementation roadmap and verified progress.
- [`adr/0001-desktop-first.md`](adr/0001-desktop-first.md): accepted desktop architecture decision.
- [`adr/0002-local-ai-and-observability.md`](adr/0002-local-ai-and-observability.md): accepted BYOK, local-data, AI-retention, and telemetry decision.
- [`adr/0003-embedded-python-runtime.md`](adr/0003-embedded-python-runtime.md): accepted self-contained Python runtime decision for macOS packages.
- [`templates/FEATURE.md`](templates/FEATURE.md): required template for new capability specifications.

## Capability specifications

- [`features/desktop-control-center.md`](features/desktop-control-center.md): onboarding, run control, live status, settings, and independent desktop UI.
- [`features/profile-vault.md`](features/profile-vault.md): candidate profile, reusable answers, documents, and credentials boundary.
- [`features/job-ingestion.md`](features/job-ingestion.md): job URL intake, extraction, normalization, and platform detection.
- [`features/evidence-and-resume.md`](features/evidence-and-resume.md): evidence ledger, requirement mapping, résumé and answer generation.
- [`features/browser-automation.md`](features/browser-automation.md): visible browser control, sessions, navigation, upload, and recovery.
- [`features/application-workflow.md`](features/application-workflow.md): durable states, checkpoints, retries, authorization, and submission.
- [`features/account-registration.md`](features/account-registration.md): candidate-account creation and existing-account handling.
- [`features/email-verification.md`](features/email-verification.md): authorized mailbox access and verification-link handling.
- [`features/ats-adapters.md`](features/ats-adapters.md): deterministic platform adapters and supported-platform contract.
- [`features/semantic-fallback.md`](features/semantic-fallback.md): generic field interpretation and confidence policy.
- [`features/human-intervention.md`](features/human-intervention.md): pause, explanation, notification, correction, resume, and cancel.
- [`features/application-tracking.md`](features/application-tracking.md): history, outcomes, artifacts, failure taxonomy, and statistics.
- [`features/evaluation-and-observability.md`](features/evaluation-and-observability.md): eval datasets, traces, metrics, regression gates, and replay.
- [`features/security-and-privacy.md`](features/security-and-privacy.md): threat boundaries, secrets, PII, consent, retention, and deletion.

## Maintenance rule

When implementation changes a capability, update its specification in the same change. When a new capability is introduced, create its document from the template and add it here before implementation. A source-code function does not need its own Markdown file; a user-visible capability or independently owned subsystem does.
