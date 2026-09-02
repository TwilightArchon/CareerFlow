# CareerFlow Threat Model

Status: baseline accepted for local development  
Last updated: 2026-08-24

## Protected assets

- Candidate identity, history, answers, resumes, and source documents.
- OpenAI API keys, Gmail OAuth tokens, ATS passwords, and the local encryption key.
- Authenticated browser sessions and application confirmation evidence.
- Submission authorization, policy decisions, checkpoints, and audit history.

## Trust boundaries

The sandboxed renderer, Electron main process, Python service, browser worker, operating-system keychain, controlled browser profile, model provider, Gmail, and applicant websites are separate trust zones. Job pages, DOM content, redirects, downloaded files, email messages, and model outputs are always untrusted data.

## Principal threats and controls

- **Local API abuse:** bind only to loopback, use a high-entropy per-launch bearer token, authenticate WebSockets and SSE, and reject browser-origin traffic.
- **Renderer compromise:** enable Chromium sandbox and context isolation, disable Node integration, apply strict CSP, and expose a narrow typed preload API.
- **Prompt injection:** send bounded data schemas to the model, never model-visible secrets, do not expose execution tools, and deterministically validate all proposals.
- **Secret disclosure:** keep secrets in macOS Keychain, redact logs and telemetry, exclude secret values from SQLite, screenshots, fixtures, and crash exports.
- **Data theft at rest:** encrypt sensitive payloads and artifacts using AES-256-GCM with unique nonces and a Keychain-held key; fail closed if the key is unavailable.
- **Hostile document import:** accept only bounded PDF/DOCX uploads, cap archive expansion/page/evidence counts, sanitize filenames, treat all extracted text as unverified, and encrypt originals before artifact storage.
- **Unsafe navigation:** allow only HTTP(S), block loopback/private-network destinations during job ingestion, validate redirects and verification links, and surface platform changes.
- **Unauthorized or duplicate side effects:** require scoped per-run authorization, stable idempotency keys, pre/post checkpoints, and confirmation inspection before retrying submission or registration.
- **CAPTCHA, 2FA, legal, or sensitive questions:** pause for human interaction and never persist challenge values.
- **Telemetry leakage:** use allowlisted attributes, bounded local retention, redaction tests, and disabled external export by default.

## Deferred release risks

The unsigned portfolio build requires manual Gatekeeper instructions and is not suitable for broad public distribution. Signing, notarization, automatic updates, Intel packaging, Gmail production OAuth verification, cloud tenancy, billing, and synchronization require a new threat-model review.

## Verification gates

Real candidate data must not be used until keychain-backed encryption, local API authentication, renderer isolation, secret scanning, redaction tests, and full deletion tests pass. Live ATS testing is limited to the owner's own applications and must never attempt to bypass platform controls.
