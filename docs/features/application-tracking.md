# Feature: Application Tracking and Statistics

Status: foundation implemented  
Owner: `apps/desktop` and `services/agent`  
Last updated: 2026-08-23

## Purpose

Maintain an accurate record of prepared, attempted, successful, unsuccessful, cancelled, and uncertain applications and turn those records into useful personal statistics.

## User flow

The dashboard lists applications with company, role, source URL, platform, timestamps, current state, resume version, interventions, outcome evidence, and failure reason. The user can filter, inspect, correct an outcome, retry a recoverable step, export data, or delete records.

## Responsibilities

- Derive current status from the append-only workflow history.
- Distinguish `submitted`, `failed`, `cancelled`, `abandoned`, and `outcome_uncertain`.
- Require confirmation evidence before reporting success.
- Classify failures by ingestion, evidence, authentication, registration, verification, mapping, validation, submission, platform change, policy, or user cancellation.
- Calculate completion rate, intervention rate, time saved, time per application, platform reliability, and failure distribution.

## Inputs and outputs

Inputs are workflow events, artifacts, platform metadata, confirmation evidence, user corrections, and later recruiting-stage updates. Outputs are application records, filtered views, aggregate statistics, exports, and retry requests.

## States and failure handling

Analytics recomputation is idempotent. Missing events or corrupted artifacts produce data-quality warnings rather than invented metrics. User outcome corrections append an audit event instead of rewriting history.

## Policy, security, and privacy

Statistics avoid exposing raw answers, credentials, email content, or unnecessary PII. Export and deletion respect artifact retention and linked profile data. Multi-user queries must always include tenant boundaries.

## Acceptance criteria

- [ ] Success is impossible without confirmation evidence or explicit user correction.
- [ ] Every failure has a stable reason code and readable explanation.
- [ ] Aggregates match underlying event records and state transitions.
- [ ] Export and deletion cover records and linked artifacts.

## Tests and evaluations

Use event-replay tests, aggregate reconciliation, duplicate-event handling, uncertain outcomes, user corrections, export/import, deletion, timezone boundaries, and tenant-isolation tests.

## Current implementation

SQLite persists application runs and append-only workflow events. An authenticated list endpoint returns up to 100 runs ordered by most recent activity, and the desktop validates and refreshes that durable projection for its queue and Applications view. Current rows show the source URL, workflow state, update time, and per-run submission permission. Job metadata, outcomes, confirmation evidence, failure classification, filters, aggregates, export, correction, and deletion remain pending.
