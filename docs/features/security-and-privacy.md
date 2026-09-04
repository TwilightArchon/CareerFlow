# Feature: Security and Privacy Controls

Status: foundation implemented  
Owner: shared platform  
Last updated: 2026-09-03

## Purpose

Protect credentials, browser sessions, resumes, email access, application answers, and user control while the agent operates untrusted websites and model services.

## Threat boundaries

- Untrusted job descriptions, DOM text, links, uploads, downloads, redirects, and email messages.
- Model output that may be wrong, injected, or structurally invalid.
- Cross-process desktop, browser-worker, and AI-service messages.
- Local malware, debug logs, crash reports, backups, and multi-user cloud services.
- External ATS, email, model, analytics, and update providers.

## Required controls

- Operating-system keychain for passwords, OAuth tokens, and encryption keys.
- Encryption at rest for local databases and artifacts; TLS for remote services.
- Typed allowlisted tool actions, least privilege, scoped authorization, and explicit policy gates.
- Strict separation between content interpretation and action execution.
- PII-aware logging, redaction tests, configurable retention, export, and deletion.
- Public-safe repository content, synthetic fixtures, and non-personal commit metadata.
- Signed desktop releases and updates before public distribution.
- Tenant isolation, authorization checks, quotas, and audit events before multi-user launch.

## Product prohibitions

Do not bypass CAPTCHA, 2FA, bot controls, access restrictions, or consent. Do not store secrets in source, configuration committed to version control, application records, logs, screenshots, traces, model prompts, or evaluation fixtures. Do not silently answer sensitive or legally meaningful questions.

## Failure handling

Token revocation, keychain failure, encryption failure, policy-service failure, or uncertain authorization fails closed. Security-relevant errors produce a user-readable recovery path without exposing secret material.

## Acceptance criteria

- [ ] A reviewed threat model exists before real candidate data is used.
- [ ] Secret scanning and redaction tests find no credential leakage.
- [ ] Untrusted content cannot expand tool permissions or alter approval policy.
- [ ] Revocation, export, retention, and deletion behavior is tested end to end.
- [ ] Multi-user release is blocked until tenant-isolation tests pass.

## Tests and evaluations

Use abuse cases, prompt-injection fixtures, unsafe URL tests, authorization matrix tests, cross-tenant tests, secret scanning, dependency scanning, local API authentication tests, encryption and key rotation tests, data deletion verification, and sanitized incident exercises.

## Current implementation

The renderer uses sandboxing, context isolation, no Node integration, strict CSP, and allowlisted IPC. The loopback API requires a high-entropy bearer token for HTTP, SSE, and WebSocket access. AES-256-GCM payload encryption is integrated with immutable candidate-profile versions and a macOS Keychain-held 256-bit key. Profile ciphertext uses ID/version-bound associated data, stale updates are rejected, and unavailable or invalid keys fail closed.

Résumé previews and imports cross the renderer boundary only as an allowlisted byte array, are capped at 10 MB, and accept only PDF/DOCX media types. First-time previews are processed in memory, return only bounded field suggestions with source spans, do not persist before consent through profile creation, and make no external or model request. PDF annotation parsing accepts only HTTP(S) LinkedIn profile and GitHub account destinations, normalizes them to HTTPS without query or fragment data, rejects credentials and non-standard ports, and never opens the links. Originals are encrypted before local artifact storage with document-ID/SHA-bound associated data. DOCX archive expansion, PDF page count, annotation count, and evidence count are bounded; filenames are reduced to basenames. Tests prove synthetic résumé statements do not occur in plaintext SQLite or artifact files. Recursive redaction, local diagnostics limits, and private-navigation rejection also have tests. Key rotation, full deletion, broader hostile-document coverage, secret scanning, and signed-runtime hardening remain pending.

Job ingestion allows only HTTP(S), validates DNS results for the initial URL and every redirect, rejects non-global destinations, limits redirect count, applies connection/read timeouts, and streams at most two megabytes of HTML. Page text is treated as data, is never executed as an instruction, and does not receive tools or model access. Telemetry records only job ID, platform, status, and counts—not description or requirement text.

Grounded material preparation runs locally and accepts only the exact current candidate-profile ID/version. It excludes unverified evidence, sensitive/legal/demographic manual facts, identity/contact/link/address facts, and contact-like imported statements. The response contains private evidence only across authenticated loopback IPC and remains ephemeral; SQLite receives no plaintext material-plan copy. Telemetry records counts and generator version, never requirement or evidence text. The deterministic draft copies verified statements verbatim and performs no model or network request.

The Safe Autofill Lab is an app-owned HTML fixture served in memory by the browser worker at a reserved `.invalid` URL. It has a restrictive content-security policy, no external resources, no submit action, and no path to an employer. Form values travel only over the authenticated loopback socket under a `sensitive` redaction policy. Canonical sensitivity is enforced again in Python instead of trusting DOM classification, contact and legal fields fail to human review, and a SHA-256 page-state hash prevents a scanned plan from filling a page that changed before execution. Durable events store counts and reason codes, not field values. Durable field explanations store only control identity, canonical mapping, confidence, sensitivity, decision, rationale, filled status, and page fingerprint; the API and UI schema contain no value property.

Application outcomes contain a constrained status, stable reason code, revision linkage, actor type, timestamp, and optional confirmation metadata. User corrections contain no free-form text. Their fingerprints are derived from non-secret run/outcome identifiers, and aggregate APIs return counts and rates only.

Run-control requests carry bounded idempotency keys and a fixed pause/resume/cancel command enum. Checkpoints contain only run identifiers, workflow state, sequence, step, idempotency, and timestamp. The worker and service both enforce paused/cancelled state, and cancel never attempts to interrupt or retry an already-submitting irreversible action.

Process recovery persists only state and idempotency metadata. It never writes browser commands or candidate field values to checkpoints. A reconnect may replay reversible navigation and synthetic filling, but account, verification, and pre-submission side effects pause for inspection; an interrupted submission becomes uncertain and cannot be retried automatically. Duplicate local commands are keyed by UUID and return a bounded in-memory cached result rather than repeating execution.

Public repository documentation is candidate-agnostic, and public commits use a GitHub noreply identity. Real profile data, private working notes, generated applications, and local artifacts remain outside version control.
