# Feature: Durable Application Workflow

Status: foundation implemented  
Owner: `services/agent`  
Last updated: 2026-08-23

## Purpose

Coordinate the full application as an explicit, recoverable state machine so browser, model, email, and human steps do not become an untraceable script.

## Canonical states

`created`, `ingesting_job`, `preparing_materials`, `opening_application`, `authenticating`, `registering`, `verifying_email`, `filling`, `awaiting_human`, `validating`, `ready_to_submit`, `submitting`, `submitted`, `failed`, `cancelled`, and `outcome_uncertain`.

## Responsibilities

- Persist state, step inputs, step outputs, attempt counts, deadlines, and transition reasons.
- Apply retries, backoff, timeouts, idempotency keys, compensation, and cancellation.
- Ask the policy engine before sensitive, ambiguous, or irreversible actions.
- Support user-authorized auto-submit for one run or configured scope; never infer submission permission.
- Require confirmation evidence before recording `submitted`.

## Inputs and outputs

Input is an application-run request containing user authorization, job, candidate version, artifact choices, and policy version. Output is an append-only transition history, current state, requested interventions, final outcome, and references to artifacts and traces.

## Failure handling

Retry only classified transient failures. Persist checkpoints before and after external side effects. If a submission request times out, inspect the page and confirmation channels before retrying; unresolved cases become `outcome_uncertain`.

## Policy, security, and privacy

Authorization is scoped, revocable, and checked again before submission. Workflow data must not contain raw credentials. Cancellation stops future actions but preserves a minimal audit trail until deletion policy applies.

## Acceptance criteria

- [ ] Every state transition is validated, persisted, and traceable.
- [ ] Process restart resumes from the last safe checkpoint.
- [ ] Duplicate submission and duplicate registration tests pass.
- [ ] Revoked authorization prevents all later controlled actions.
- [ ] Success requires verifiable confirmation evidence.

## Tests and evaluations

Use transition-table tests, property tests for invalid transitions, injected crashes at every boundary, timeout/retry tests, cancellation races, duplicate-side-effect tests, and trace completeness checks.

## Current implementation

Canonical states and allowed transitions are enforced in a service layer. Runs and append-only events persist in SQLite, transition idempotency is protected by unique keys, and `submitting` is rejected without per-run authorization. Browser navigation moves an immediate run through the initial states and records its result. The desktop restores and refreshes current run states from the durable store after relaunch. Durable execution resumption, checkpoints, explicit queue ordering, cancellation, retries, timeouts, LangGraph execution, and crash-injection coverage remain pending.
