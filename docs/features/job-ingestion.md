# Feature: Job Ingestion and Platform Detection

Status: proposed  
Owner: `services/agent` and `packages/browser-worker`  
Last updated: 2026-08-22

## Purpose

Turn a user-provided job URL into a normalized, traceable job record and identify the likely application platform and entry point.

## User flow

The user pastes a URL. CareerFlow validates it, loads the public page or visible browser page, extracts the role, company, location, description, qualifications, compensation when present, and application link, then shows a summary for correction before preparation begins.

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

- [ ] Supported fixtures produce correct normalized fields and requirement spans.
- [ ] Platform detection reports confidence and never silently selects an incompatible adapter.
- [ ] Expired, inaccessible, or non-job URLs produce clear outcomes.
- [ ] Duplicate job records are linked rather than silently recreated.

## Tests and evaluations

Use structured-data, plain HTML, dynamic page, redirect, expired, login-wall, malicious-instruction, and changed-content fixtures. Measure field accuracy and requirement span coverage.
