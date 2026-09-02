# Feature: Security and Privacy Controls

Status: foundation implemented  
Owner: shared platform  
Last updated: 2026-09-02

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

Résumé imports cross the renderer boundary only as an allowlisted byte array, are capped at 10 MB, and accept only PDF/DOCX media types. Originals are encrypted before local artifact storage with document-ID/SHA-bound associated data. DOCX archive expansion, PDF page count, and evidence count are bounded; filenames are reduced to basenames. Tests prove synthetic résumé statements do not occur in plaintext SQLite or artifact files. Recursive redaction, local diagnostics limits, and private-navigation rejection also have tests. Key rotation, full deletion, hostile-link coverage, secret scanning, and signed-runtime hardening remain pending.

Public repository documentation is candidate-agnostic, and public commits use a GitHub noreply identity. Real profile data, private working notes, generated applications, and local artifacts remain outside version control.
