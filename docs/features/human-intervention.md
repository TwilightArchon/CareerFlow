# Feature: Human Intervention and Resume

Status: user-requested pause foundation implemented
Owner: `apps/desktop` and `services/agent`  
Last updated: 2026-08-22

## Purpose

Pause a run safely when CareerFlow needs human action or judgment, explain exactly what is needed, and resume from a durable checkpoint afterward.

## Intervention categories

CAPTCHA, 2FA, OAuth consent, mailbox ambiguity, legal attestation, demographic or disability question, salary or sponsorship policy, unsupported claim, low-confidence field mapping, site change, validation conflict, expired session, uncertain external side effect, and user-requested pause.

## Responsibilities

- Show the reason, affected application, current page, blocked action, available choices, risk, and proposed value when applicable.
- Notify the user without exposing sensitive content on a lock screen.
- Let the user edit, approve once, save a reusable policy where allowed, reject, retry, open the browser, or cancel.
- Detect completion of manual browser steps and re-inspect before resuming.
- Preserve the exact checkpoint and invalidate stale responses after page changes.

## Inputs and outputs

Input is a typed intervention request with policy reason and safe context. Output is a signed, time-bounded response and optional profile correction or reusable policy update. Raw CAPTCHA or 2FA secrets are not persisted.

## States and failure handling

States include `requested`, `notified`, `viewed`, `responded`, `expired`, `withdrawn`, and `resolved`. Duplicate responses are idempotent; stale responses cannot resume a changed page.

## Policy, security, and privacy

Only the owning user may resolve an intervention. Sensitive answers are masked and excluded from notifications and analytics. Reusable policies show scope and can be revoked.

## Acceptance criteria

- [ ] Every policy pause has an understandable reason and clear next action.
- [ ] Resuming revalidates page state and authorization.
- [ ] Stale or duplicate responses cannot execute the blocked action twice.
- [ ] CAPTCHA and 2FA values are not stored in durable records.

## Tests and evaluations

Test every category, notification redaction, session restart, stale page, duplicate response, manual browser completion, cancellation race, policy reuse, and accessibility with keyboard and screen reader flows.

## Current implementation

The desktop provides explicit pause, resume, and cancel actions for active runs. User pause persists a typed checkpoint containing the exact resumable state, moves the run to `paused`, and sends an idempotent browser-control command. Resume requires the browser worker, restores only the checkpointed state, and rescans the synthetic form instead of assuming its page is unchanged. Cancel is terminal and records a constrained cancellation outcome. Browser and workflow gates reject stale automated work while paused or cancelled. Browser-worker recovery also pauses authentication, registration, verification, and ready-to-submit states rather than guessing whether an external side effect completed; the existing run card exposes the same resume/cancel controls while the dedicated intervention record and explanation UI remain pending.

Policy-generated intervention records, expiry, notifications, corrected-value references, automatic manual-step detection, and reusable answer policies remain pending.
