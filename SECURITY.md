# Security Policy

CareerFlow handles credentials, browser sessions, resumes, email verification, and sensitive application answers. Security and privacy defects are treated as release blockers.

## Do not commit sensitive data

Never commit real credentials, OAuth tokens, browser profiles, resumes, application answers, email content, screenshots containing personal data, or production traces. Use synthetic fixtures.

Public planning documents must describe product goals without copying candidate-specific résumé details. Public commits should use the repository owner's GitHub-provided noreply address so ordinary commit metadata does not disclose a personal email address. If private data reaches public Git history, sanitizing only the latest file is insufficient; rewrite the reachable history and rotate any exposed credential.

## Reporting a vulnerability

This repository does not yet have a public disclosure channel. Until one is established, do not open a public issue containing exploit details or personal data. The repository owner must define a private contact method before public distribution.

## Required response

- Stop affected automation when authorization, encryption, secret storage, tenant isolation, or outcome integrity is uncertain.
- Preserve only redacted diagnostic evidence.
- Add a regression test and update `docs/features/security-and-privacy.md` when the fix changes a security boundary or control.
- Rotate exposed secrets through the provider or operating-system keychain; never attempt to solve exposure by deleting only a repository file.

The planned controls and security acceptance criteria are maintained in `docs/features/security-and-privacy.md`.
