# Feature: Job Ingestion and Platform Detection

Status: deterministic public-page foundation implemented
Owner: `services/agent` and `packages/browser-worker`  
Last updated: 2026-09-02

## Purpose

Turn a user-provided job URL into a normalized, traceable job record and identify the likely application platform and entry point.

## User flow

The user pastes a URL and selects **Review role**. CareerFlow validates and loads the public page, extracts structured job metadata and deterministic requirements, and shows title, company, location, platform confidence, warnings, and requirement classifications before the user confirms browser navigation. The user may return to edit the URL. Field-level correction remains pending.

## Responsibilities

- Resolve redirects and distinguish job description, listing, authentication, and application pages.
- Prefer structured metadata and deterministic parsing before model extraction.
- Preserve raw text, URL, retrieval time, content hash, and source spans.
- Normalize requirements without inventing missing details.
- Detect supported ATS platforms and report confidence and capabilities.

## Inputs and outputs

Input is a URL plus the authorized browser context when the page requires it. Output is a versioned job record, requirement list, platform classification, content snapshot reference, and extraction diagnostics.

## States and failure handling

States include `validating`, `loading`, `extracting`, `needs_user`, `complete`, and `failed`. Handle expired postings, login walls, redirects, duplicate URLs, unsupported protocols, bot challenges, and changed content without treating partial extraction as complete.

## Policy, security, and privacy

Page content is untrusted and cannot issue instructions to the agent. URL fetching must block unsafe local-network access and non-web schemes. Retain only content needed to prepare and audit the application.

## Acceptance criteria

- [x] Supported fixtures produce correct normalized fields and requirement spans. (Structured JSON-LD and flattened Workday metadata are covered.)
- [x] Platform detection reports confidence and never silently selects an incompatible adapter. (Hostname detection reports Workday, Greenhouse, Lever, or `unknown`; adapter execution is not yet enabled.)
- [ ] Expired, inaccessible, or non-job URLs produce clear outcomes.
- [x] Duplicate job records are linked rather than silently recreated. (Identical canonical URL/content returns the existing record; changed content creates a version linked by `supersedesId`.)

## Tests and evaluations

Use structured-data, plain HTML, dynamic page, redirect, expired, login-wall, malicious-instruction, and changed-content fixtures. Measure field accuracy and requirement span coverage.

## Current implementation

The authenticated local API performs a bounded two-megabyte HTTP retrieval with explicit timeouts, at most five redirects, HTTP(S)-only URLs, DNS resolution on every redirect, and rejection of loopback, private, link-local, reserved, or otherwise non-global targets. It prefers Schema.org `JobPosting` JSON-LD, then Open Graph metadata, then bounded visible text. Deterministic parsing normalizes the title, company, location, description hash, canonical/resolved URLs, platform signals, warnings, and source-spanned required/preferred statements. It handles both structured HTML lists and Workday's flattened metadata representation without calling OpenAI.

SQLite stores versioned job records. Re-ingesting identical canonical content returns the existing record, while changed content creates a new version linked to the prior record. Confirming the desktop review creates a run using the durable job ID and opens the resolved URL in the visible browser. Runs now display the normalized role, company, and platform when available.

Dynamic-page browser extraction, explicit expired/login-wall classification beyond HTTP status, content-snapshot encryption/retention controls, user correction, compensation extraction, and application-link discovery remain pending. Incomplete deterministic results are labeled `needs_review` rather than silently completed.
