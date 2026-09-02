# Feature: Email Verification Connector

Status: proposed  
Owner: `services/agent`  
Last updated: 2026-08-22

## Purpose

Use user-authorized mailbox access to locate and validate application-related verification messages, then open the correct link in the controlled browser without exposing unrelated email.

## User flow

The user connects Gmail through OAuth during onboarding or at first use. When registration expects a message, CareerFlow searches a narrow time and sender window, presents an intervention if multiple messages match, and opens the verified link. The user can disconnect access at any time.

## Responsibilities

- Start with a Gmail connector and keep the interface provider-neutral.
- Request the least privilege that supports narrowly scoped message lookup.
- Match messages against run context, expected employer or platform domain, recipient, time window, and link host.
- Store message and link fingerprints rather than full mailbox content when possible.
- Handle delayed, duplicate, expired, and malformed verification messages.

## Inputs and outputs

Inputs are an OAuth token reference, expected sender/domain, recipient, registration time, and run identifier. Output is a validated verification URL fingerprint and action result, or a human intervention. Full message content is not a workflow output.

## States and failure handling

States include `disconnected`, `authorized`, `waiting`, `matched`, `needs_human`, `verified`, `expired`, and `failed`. Polling is bounded and cancellable. Token revocation, consent changes, API limits, and multiple matches pause safely.

## Policy, security, and privacy

OAuth tokens live in the OS keychain. Do not send email bodies or verification URLs to a model. Do not read, modify, delete, label, or send unrelated messages. Validate links against expected HTTPS hosts before opening.

## Acceptance criteria

- [ ] Unrelated messages are not persisted or exposed to model context.
- [ ] Ambiguous matches require user selection.
- [ ] Revoking mailbox access stops polling and future reads.
- [ ] Expired and duplicate links produce classified recoverable outcomes.

## Tests and evaluations

Use a fake mailbox provider for exact match, delayed arrival, duplicate messages, hostile links, expired links, revoked tokens, API limits, cancellation, and redaction tests.
