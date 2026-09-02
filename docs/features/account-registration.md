# Feature: Candidate Account Registration

Status: proposed  
Owner: `packages/browser-worker` and `services/agent`  
Last updated: 2026-08-22

## Purpose

Create or recover applicant accounts when an ATS requires one, using user-configured identity and credential policies while avoiding duplicate accounts and unsafe password handling.

## User flow

The user configures preferred usernames, email identity, and credential policy during onboarding. During a run, CareerFlow detects whether an account exists, signs in when authorized, or proposes and creates an account. It pauses for CAPTCHA, 2FA, unavailable usernames, unknown account state, or required consent outside the saved policy.

## Responsibilities

- Detect sign-in, registration, password-reset, and existing-account conditions.
- Generate or select credentials according to the configured policy; prefer unique passwords per employer.
- Store credential records in the operating-system keychain and only secret references in workflow state.
- Avoid duplicate creation through employer/domain identity keys and pre/post checks.
- Record account-creation outcome without logging the credential.

## Inputs and outputs

Inputs are the platform, employer domain, user identity, preferred username rules, keychain secret reference, and authorization. Outputs are an authenticated browser session, account metadata, secret reference, or a classified intervention/failure.

## States and failure handling

Handle username conflicts, password constraints, pre-existing accounts, locked accounts, expired sessions, registration emails, failed verification, and ambiguous success. Irreversible retries require idempotency checks.

## Policy, security, and privacy

Never reuse a password unless the user explicitly configured that behavior and acknowledged the risk. Never display, log, trace, or send a password to a model. Terms or legal attestations require a saved explicit policy or intervention.

## Acceptance criteria

- [ ] Raw credentials exist only in memory for the required operation and in the OS keychain.
- [ ] Duplicate-account scenarios do not create a second account.
- [ ] CAPTCHA and 2FA always pause for the user.
- [ ] Registration can resume safely after email verification or process restart.

## Tests and evaluations

Use local fixtures for new account, existing account, duplicate identity, password constraints, username conflict, expired session, CAPTCHA, 2FA, consent, timeout, and uncertain outcome.
