# Feature: Candidate Profile and Evidence Vault

Status: encrypted profile and résumé-evidence foundation implemented  
Owner: `services/agent` and `apps/desktop`  
Last updated: 2026-08-24

## Purpose

Maintain the verified personal data, source documents, reusable answers, preferences, and evidence that CareerFlow may use in applications.

## User flow

The user imports a resume or enters information, reviews extracted records, corrects errors, and approves reusable answers. Every claim links to a source or explicit user statement. The user can edit, export, or delete the profile.

## Responsibilities

- Normalize identity, contact, education, employment, projects, skills, links, authorization, and preferences into versioned typed records.
- Preserve source document, page or section, source span, extraction method, confidence, and user-verification status.
- Separate ordinary reusable answers from sensitive or application-specific answers.
- Store secret references, never raw passwords or OAuth tokens.
- Prevent unverified evidence from becoming an asserted application claim without review.

## Inputs and outputs

Inputs include PDF/DOCX resumes, user-entered profile fields, verified corrections, and saved answer policies. Outputs are versioned candidate facts, evidence items, document artifacts, and secret references consumed by evidence mapping, registration, and form filling.

## States and failure handling

Imported facts move through `extracted`, `needs_review`, `verified`, `superseded`, or `deleted`. Re-import must not silently overwrite verified edits. Parsing failures retain the source artifact and provide a retry or manual-entry path.

## Policy, security, and privacy

Local records and artifacts are encrypted at rest. Credentials live in the operating-system keychain. Logs and model prompts receive the minimum required fields. Export and deletion must include derived artifacts and explain any retained audit metadata.

## Acceptance criteria

- [ ] Every generated claim can be traced to verified evidence.
- [ ] Re-import preserves user corrections and version history.
- [ ] No raw credential appears in the database, logs, traces, or model context.
- [ ] The user can export and delete their stored profile and documents.

## Tests and evaluations

Use parser fixtures, schema round trips, provenance coverage checks, duplicate reconciliation tests, encryption checks, and PII redaction tests.

## Current implementation

Canonical profile, fact, evidence, source-document, and source-span schemas exist. The desktop onboarding form captures identity, contact, location, links, one education entry, and optional explicit work-authorization answers. Each entered field becomes a verified user-sourced fact with sensitivity classification and evidence linkage.

One stable profile ID has immutable versions. Canonical profile JSON is encrypted with AES-256-GCM and version-bound associated data before SQLite storage; the database contains ciphertext, a non-secret Keychain reference, and timestamps. The 256-bit key exists only in macOS Keychain. Reads and writes fail closed when the key is missing or invalid, and optimistic version checks prevent stale edits. Authenticated typed local APIs and the narrow Electron preload expose only load and save operations. New application runs reference the current real profile ID and version.

Selectable-text PDF and DOCX résumés can now be imported from the sandboxed desktop UI. The original bytes are encrypted with AES-256-GCM into local artifact storage, while the immutable profile version records only metadata and the encrypted artifact reference. Deterministic extraction creates one reviewable evidence item per PDF line, DOCX paragraph, heading, or table row. Each item records its source-document ID, normalized character offsets, page or section, extraction method, confidence, and verification state. Imported evidence never overwrites manually verified facts; verification creates another immutable profile version. Duplicate content is rejected by SHA-256, unsafe filenames are reduced to their basename, uploads are capped at 10 MB, parser work is bounded, and image-only PDFs are retained as `needs_ocr`.

Tests cover encryption round trips, plaintext absence from SQLite and encrypted artifacts, packaged Keychain restart restoration, version preservation, stale writes, missing keys, PDF/DOCX provenance, tables, duplicate imports, image-only PDFs, evidence verification, recursive redaction, API round trips, and contract validation. Multiple education/employment entries, OCR, export, deletion, richer re-import reconciliation, credential management, and key rotation remain pending.
