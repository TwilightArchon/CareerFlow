# Feature: ATS Adapters

Status: proposed  
Owner: `packages/browser-worker/adapters`  
Last updated: 2026-08-22

## Purpose

Provide deterministic, versioned automation for known applicant-facing platforms while containing platform-specific selectors and navigation behavior behind one contract.

## Initial platforms

Workday is the first planned production adapter, followed by Greenhouse and Lever. Other platforms are added only with fixtures, capability documentation, and measurable reliability.

## Adapter contract

An adapter detects platform and version signals; inspects the current step; returns normalized fields and constraints; fills approved values; uploads approved artifacts; navigates; reports validation; detects authentication, registration, review, challenge, and confirmation states; and supplies diagnostic evidence.

## Responsibilities

- Prefer roles, labels, stable attributes, and page semantics over brittle visual position or generated class names.
- Separate inspection from execution so policy can approve the action plan.
- Publish supported capabilities and known limitations per platform version.
- Fail closed to semantic fallback or human intervention when confidence drops.
- Maintain offline sanitized fixtures for regression tests.

## Inputs and outputs

Inputs are the current page snapshot, approved canonical field map, artifacts, and action scope. Outputs are observed controls, action results, validation errors, platform/version signals, confirmation evidence, and structured unsupported-state reasons.

## Policy, security, and privacy

Adapters cannot decide legal or sensitive answers and cannot bypass platform controls. Fixtures use synthetic data. Platform changes discovered in real use must be sanitized before becoming test cases.

## Acceptance criteria

- [ ] Each supported adapter publishes a tested capability matrix.
- [ ] Required-field and validation behavior is represented in fixtures.
- [ ] Platform changes fail visibly instead of producing silent wrong fills.
- [ ] Adapter code contains no user-specific data or secrets.

## Tests and evaluations

Use contract tests shared by all adapters, per-platform fixtures, selector mutation tests, multi-page end-to-end tests, upload tests, validation tests, and historical regression replay. Report field accuracy and completion rate by adapter version.
