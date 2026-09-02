# ADR 0001: Desktop-First Application Operator

Status: accepted  
Date: 2026-08-22

## Context

CareerFlow needs an independent UI, user-controlled local browser sessions, secure credential access, reliable long-running workflows, file handling, and intervention notifications. A browser extension alone would make the dashboard and orchestration experience fragmented; a cloud-only service would require remote custody of sensitive sessions and credentials.

## Decision

Use an Electron + React + TypeScript desktop application as the control center. Use a separate visible Playwright-controlled Chromium profile for application execution. Use a Python FastAPI service for document/AI processing and workflow orchestration, connected through versioned local APIs.

The initial release targets macOS 14+ on Apple Silicon, Node.js 24 LTS, pnpm, Python 3.13, and uv. Each installation executes locally and owns one active application run plus a reorderable queue. There is no centralized browser executor or browser extension.

Keep domain workflow states independent of LangGraph so the engine can later move to Temporal or another durable runtime. Keep the browser worker and local secrets on the user's device when the project adds a multi-user cloud control plane.

The local API binds only to loopback on an ephemeral port and requires a random per-launch bearer token. OpenTelemetry trace context crosses Electron, FastAPI, and the browser worker. External telemetry export is disabled by default.

## Consequences

- The user gets one independent interface for setup, operation, intervention, and statistics.
- Browser activity remains visible and can be paused or cancelled.
- TypeScript is used for the desktop and browser surface; Python is used for the AI and evaluation ecosystem.
- Packaging two runtimes increases build complexity and must be proven in Phase 1.
- The local API and process lifecycle require authentication, health checks, restart behavior, and version compatibility.
- Electron has a larger distribution footprint than Tauri, but avoids adding a third implementation language and aligns closely with Playwright.

## Alternatives considered

- Browser extension plus web dashboard: simpler page access, but fragmented product state and weaker independent-app experience.
- Tauri plus React: smaller binaries, but introduces Rust and still requires TypeScript/Python side processes.
- Cloud-only browser automation: easier centralized scaling, but higher security, cost, session-transfer, and platform-compliance risk.

## Acceptance conditions

- A packaged prototype can start and supervise both the browser worker and Python service.
- Credentials remain in the operating-system keychain.
- A run survives UI reload and can recover from a worker restart.
- The architecture can later separate a local executor from a multi-tenant control plane.
