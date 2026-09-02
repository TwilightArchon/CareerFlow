# ADR 0002: Local AI Credentials and Privacy-Preserving Observability

Status: accepted  
Date: 2026-08-23

## Context

CareerFlow processes resumes, application answers, browser sessions, and credentials. The portfolio release must demonstrate AI and production observability without introducing a central service that stores private candidate data, browser sessions, or shared model credentials.

## Decision

Each installation executes independently and stores its private state locally. Users provide their own OpenAI API key, which remains in macOS Keychain. Model requests use the Responses API with strict structured outputs, medium reasoning by default, no execution tools, and `store=false`.

OpenTelemetry spans and metrics cross Electron, FastAPI, browser, policy, workflow, document, and model boundaries using W3C trace context. Development may export OTLP to a loopback Collector and Jaeger. Packaged builds retain only bounded redacted local diagnostics unless the user explicitly exports them. External telemetry is disabled by default.

Application history and user-facing statistics are derived from append-only workflow events, not telemetry, because traces and metrics may be sampled or dropped.

## Consequences

- There is no centralized browser-session or candidate-data custody in the portfolio release.
- Model cost belongs to the user's API account and can be explained per run.
- Telemetry remains useful for engineering without becoming the source of business truth.
- Support diagnostics require an explicit local export and must preserve redaction.
- Multi-device synchronization, shared analytics, billing, and remote support require a later privacy and tenancy decision.
