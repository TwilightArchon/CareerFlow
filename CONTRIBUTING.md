# Contributing to CareerFlow

CareerFlow is currently a personal portfolio project designed for later multi-user use. Contributions should preserve user control, truthfulness, recoverability, and privacy.

## Before making a change

1. Read `AGENTS.md` and `docs/INDEX.md`.
2. Read the relevant feature specifications and architecture decision records.
3. Confirm the work belongs to the current phase in `TODO.md`.
4. Add a feature specification from `docs/templates/FEATURE.md` if no current document owns the behavior.

## Change requirements

- Keep implementation, tests, feature docs, architecture docs, and TODO status synchronized.
- Add regression coverage for fixed bugs.
- Use synthetic data in tests, screenshots, fixtures, and demonstrations.
- Keep provider-specific ATS behavior behind the adapter contract.
- Do not add real resumes, application answers, credentials, OAuth tokens, browser profiles, or mailbox content to the repository.
- Record expensive-to-reverse decisions as ADRs under `docs/adr/`.

## Validation

Build, lint, type-check, test, and packaging commands will be added after the initial workspace is scaffolded. Do not invent or document a command as verified until it has run successfully in a clean environment.

Before declaring a change complete, verify its acceptance criteria in the relevant feature file and update `TODO.md` only for criteria supported by evidence.
