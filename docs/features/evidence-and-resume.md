# Feature: Evidence Mapping and Application Materials

Status: deterministic evidence mapping and review-draft foundation implemented
Owner: `services/agent`  
Last updated: 2026-09-03

## Purpose

Map job requirements to verified candidate evidence and generate truthful, ATS-readable resumes and application answers with inspectable provenance.

## User flow

CareerFlow ranks relevant evidence for each requirement, highlights supported and unsupported requirements, prepares a resume and draft answers, and shows why each claim was included. The user can accept, edit, or reject drafts; accepted corrections may be saved as new verified evidence.

## Responsibilities

- Retrieve and rank evidence by relevance, recency, strength, and source quality.
- Generate only from supplied evidence and structured job requirements.
- Validate dates, entities, metrics, length limits, and unsupported claims deterministically.
- Version prompts, models, input evidence, generated artifacts, and user edits.
- Produce simple selectable-text documents with conventional sections and no claim of a universal ATS score.

## Inputs and outputs

Inputs are the normalized job, verified candidate evidence, document template, answer policy, and model configuration. Outputs are requirement-to-evidence mappings, unsupported-gap flags, draft answers, a versioned resume artifact, and field-level citations for internal review.

## States and failure handling

Generation may be `drafting`, `validating`, `needs_review`, `approved`, or `rejected`. Unsupported claims, contradictory dates, missing evidence, parser failures, and model timeouts must stop the affected artifact without blocking unrelated deterministic fields.

## Policy, security, and privacy

Candidate data sent to model providers must be minimized and governed by configured retention settings. Open-ended answers that assert new experience require explicit review. Models cannot update verified evidence directly.

## Acceptance criteria

- [ ] Unsupported-claim count is zero in the release evaluation set.
- [ ] Every material resume bullet and open-ended answer has evidence provenance.
- [x] Resume parsing fixtures recover the intended sections and fields. (Selectable PDF pages and DOCX headings, paragraphs, and table rows are covered with source spans.)
- [ ] User edits create a new version and never erase source history.

## Tests and evaluations

Use retrieval relevance metrics, citation coverage, contradiction checks, unsupported-claim graders, snapshot tests for documents, parser round trips, adversarial jobs, and human review samples.

## Current implementation

The OpenAI boundary uses the Responses API with `store=false`, medium reasoning, a user-selected model defaulting to `gpt-5.6-terra`, strict Pydantic outputs, token/latency telemetry, and no execution tools.

Deterministic local parsing creates a provenance-backed evidence ledger from selectable-text PDFs, allowlisted LinkedIn/GitHub PDF hyperlink annotations, and DOCX paragraphs, headings, and table rows. Annotation-derived links retain their page and a `hyperlink` section marker. The same parser supports a non-persistent résumé-first preview that suggests common profile fields with source spans and no model call or token use. Extracted statements are unverified by default and the desktop user can explicitly verify or return each item to review; every change creates a new encrypted profile version. Source files are encrypted locally after profile creation and no résumé contents are sent to OpenAI. Image-only PDFs are recognized but await OCR.

The authenticated material-preparation endpoint now validates the exact current profile ID/version and job ID/version, excludes unverified evidence, excludes manual facts outside ordinary education, filters contact-like statements, and deterministically ranks remaining evidence using normalized requirement-term coverage. Each requirement reports `supported`, `partial`, or `unsupported`, a bounded confidence score, matched terms, exact evidence IDs, and source spans. The draft contains only verbatim verified statements selected from non-unsupported mappings, so the deterministic baseline cannot introduce a new claim. OpenTelemetry records only structural counts and generator metadata.

The material plan is recomputable and remains in renderer memory rather than duplicating private statements into plaintext SQLite. It is always `needs_review`, or `needs_evidence` when no eligible verified evidence exists; changing the profile invalidates it. Model-assisted rewriting, deterministic unsupported-claim validation for rewritten prose, user draft edits, encrypted durable material versions, requirement-retrieval evaluation, and DOCX/PDF rendering remain pending.
