# Feature: Evaluation and Observability

Status: foundation implemented  
Owner: shared platform  
Last updated: 2026-08-25

## Purpose

Make probabilistic quality, workflow reliability, browser failures, latency, cost, and user outcomes measurable enough to gate releases and debug individual runs.

## Responsibilities

- Correlate model calls, browser actions, policy decisions, workflow transitions, interventions, and outcomes under one trace.
- Record model, prompt, schema, and adapter versions, latency, tokens, cost estimate, retries, error class, and redacted inputs and outputs.
- Maintain golden datasets for job extraction, evidence retrieval, unsupported claims, field mapping, policy, and end-to-end workflows.
- Convert reviewed production failures into sanitized regression cases.
- Gate releases on deterministic tests and agreed evaluation thresholds.

## Inputs and outputs

Inputs are structured telemetry events, sanitized fixtures, grader definitions, expected outputs, and user corrections. Outputs are traces, dashboards, evaluation reports, comparisons, alerts, and replayable regression cases.

## Failure handling

Telemetry failure must not authorize or block actions incorrectly. Buffer bounded local events, expose dropped-event counts, and avoid retry storms. Evaluation runs are reproducible by dataset, configuration, prompt, model, and code version.

## Policy, security, and privacy

Redact credentials, tokens, CAPTCHA and 2FA values, sensitive answers, unnecessary DOM text, full email bodies, and personal document content. Access to traces and fixtures follows the same tenant and deletion boundaries as application data.

## Acceptance criteria

- [ ] A failed run can be reconstructed from redacted events and artifact references.
- [ ] Every model and browser action has latency, outcome, version, and trace correlation.
- [ ] CI blocks regressions beyond accepted thresholds.
- [ ] Production-derived fixtures are synthetic or sanitized and reviewed.

## Tests and evaluations

Test trace completeness, redaction, sampling, dropped-event behavior, metric reconciliation, reproducibility, grader stability, release gates, and replay across version changes.

## Current implementation

Electron, FastAPI, and the browser worker initialize OpenTelemetry SDKs and propagate W3C context. Workflow, policy, browser, and OpenAI boundaries define initial spans and metrics. Development OTLP configuration feeds a local collector and Jaeger. Python also writes bounded redacted local span diagnostics, with a test proving secret redaction. Full cross-process trace assertions, metric reconciliation, model-cost calculation, replay UI, and evaluation datasets remain pending.

The GitHub Actions verification job installs the pinned pnpm release before enabling setup-node's pnpm cache, uses Node-24-backed action releases, prints the resolved toolchain versions, installs both lockfiles in frozen mode, regenerates and checks deterministically formatted contracts, and runs formatting, typing, tests, and production builds. A repository check validates the setup ordering and required pins before changes reach CI. Evaluation-threshold release gates remain pending.
