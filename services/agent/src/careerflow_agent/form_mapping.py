from __future__ import annotations

import re

from .contracts import (
    BrowserFieldFill,
    CandidateProfile,
    FieldMapping,
    FormControl,
    MappingDecision,
    ObservedForm,
)
from .policy import evaluate_mapping
from .profile_vault import FIELD_SENSITIVITY

_ALIASES: tuple[tuple[str, tuple[str, ...], str | None], ...] = (
    ("identity.first_name", ("first name", "given name"), "given-name"),
    ("identity.last_name", ("last name", "family name", "surname"), "family-name"),
    ("contact.email", ("email", "email address"), "email"),
    ("contact.phone", ("phone", "phone number", "mobile"), "tel"),
    ("links.linkedin", ("linkedin", "linkedin profile"), None),
    ("links.github", ("github", "github profile"), None),
    ("education.0.school", ("school", "university", "college"), "organization"),
    ("education.0.degree", ("degree",), None),
    ("education.0.field_of_study", ("field of study", "major"), None),
    ("education.0.graduation_year", ("graduation year", "graduation date"), None),
    ("work_authorization.status", ("work authorization", "authorized to work"), None),
    (
        "work_authorization.requires_sponsorship",
        ("sponsorship", "require sponsorship"),
        None,
    ),
)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def map_control(control: FormControl) -> FieldMapping:
    label = _normalized(control.label)
    autocomplete = _normalized(control.autocomplete or "")
    for canonical_path, aliases, autocomplete_hint in _ALIASES:
        if autocomplete_hint and autocomplete == _normalized(autocomplete_hint):
            confidence = 0.99
            rationale = f"Autocomplete metadata identifies {canonical_path}."
            break
        if any(alias == label or alias in label for alias in aliases):
            confidence = 0.98
            rationale = f"The visible label deterministically matches {canonical_path}."
            break
    else:
        return FieldMapping(
            control_id=control.control_id,
            canonical_path=None,
            source="deterministic",
            confidence=0,
            sensitivity=control.sensitivity,
            decision=MappingDecision.UNSUPPORTED,
            rationale="No deterministic canonical-field rule matched this control.",
        )

    proposal = FieldMapping(
        control_id=control.control_id,
        canonical_path=canonical_path,
        source="deterministic",
        confidence=confidence,
        sensitivity=FIELD_SENSITIVITY[canonical_path],
        decision=MappingDecision.REVIEW,
        rationale=rationale,
    )
    policy = evaluate_mapping(proposal)
    return proposal.model_copy(update={"decision": policy.decision})


def plan_form_fill(
    observed_form: ObservedForm, profile: CandidateProfile
) -> tuple[list[BrowserFieldFill], list[FieldMapping], list[FieldMapping]]:
    facts = {
        fact.canonical_path: fact
        for fact in profile.facts
        if fact.state == "verified" and fact.value
    }
    fills: list[BrowserFieldFill] = []
    mappings: list[FieldMapping] = []
    blocked: list[FieldMapping] = []
    for control in observed_form.controls:
        mapping = map_control(control)
        mappings.append(mapping)
        fact = facts.get(mapping.canonical_path or "")
        if mapping.decision is MappingDecision.AUTO_FILL and fact is not None:
            fills.append(
                BrowserFieldFill(
                    control_id=control.control_id,
                    canonical_path=fact.canonical_path,
                    value=fact.value,
                    evidence_ids=fact.evidence_ids,
                    rationale=mapping.rationale,
                )
            )
        elif control.required or fact is not None:
            blocked.append(mapping)
    return fills, mappings, blocked
