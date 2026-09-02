# Feature: Semantic Form Fallback

Status: proposed  
Owner: `packages/browser-worker` and `services/agent`  
Last updated: 2026-08-22

## Purpose

Interpret conventional fields on unknown or customized application forms when no deterministic ATS adapter applies, without giving a model direct control of the browser.

## Interpretation flow

1. Extract visible label, instructions, input type, name, ID, placeholder, ARIA data, autocomplete metadata, section headings, options, required status, limits, and validation messages.
2. Apply deterministic rules to map controls to canonical fields.
3. Ask a model for structured classification only when deterministic evidence is insufficient.
4. Validate the proposed mapping and assign confidence and sensitivity classes.
5. Policy chooses `auto_fill`, `review`, `human_required`, or `unsupported` before the browser acts.

## Responsibilities

- Map controls to canonical paths such as `identity.first_name` or `work_authorization.requires_sponsorship`.
- Explain the evidence and confidence behind each mapping.
- Recognize repeated education/employment groups and conditional sections.
- Detect contradictory labels, hidden traps, hostile page instructions, and unsupported custom widgets.
- Never generate a candidate value; it maps fields and retrieves approved values only.

## Inputs and outputs

Input is a sanitized semantic page representation. Output is a typed mapping proposal containing canonical field, control reference, confidence, sensitivity, rationale, constraints, and recommended action class.

## Policy, security, and privacy

DOM content is untrusted and may contain prompt injection. Models receive a bounded schema and cannot request tools, secrets, or policy changes. Sensitive and legal fields require explicit policy regardless of mapping confidence.

## Acceptance criteria

- [ ] High-confidence deterministic mappings meet the release accuracy threshold.
- [ ] Unsupported or ambiguous controls pause instead of receiving guessed values.
- [ ] All model proposals pass schema and policy validation before execution.
- [ ] Prompt-injection fixtures cannot change tool permissions or reveal data.

## Tests and evaluations

Use labeled field datasets, multilingual and unusual-label fixtures, custom widgets, repeated groups, conditional sections, adversarial instructions, calibration curves, false-fill rate, abstention rate, and user-correction rate.
