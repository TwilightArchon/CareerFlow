from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from .contracts import (
    ApplicationMaterialPlan,
    CandidateProfile,
    EvidenceItem,
    EvidenceMatch,
    GroundedResumeDraft,
    GroundedResumeEntry,
    JobPosting,
    JobRequirement,
    MaterialPlanStatus,
    RequirementEvidenceMapping,
    RequirementSupport,
    Sensitivity,
)

GENERATOR_VERSION = "deterministic-v1"
MAX_MATCHES_PER_REQUIREMENT = 3
MAX_DRAFT_ENTRIES = 12
MIN_EVIDENCE_LENGTH = 8
MAX_EVIDENCE_LENGTH = 1_000

TOKEN_PATTERN = re.compile(r"[a-z0-9+#.]+")
CONTACT_PATTERN = re.compile(
    r"(?:https?://|www\.|[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d))",
    re.IGNORECASE,
)
SENSITIVE_EVIDENCE_PATTERN = re.compile(
    r"\b(?:authorized to work|citizenship|date of birth|disability|ethnicity|gender|race|"
    r"sexual orientation|sponsorship|visa status|veteran status|work authori[sz]ation)\b",
    re.IGNORECASE,
)
STOP_TERMS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "candidate",
    "demonstrated",
    "experience",
    "for",
    "from",
    "have",
    "in",
    "is",
    "job",
    "knowledge",
    "of",
    "on",
    "or",
    "preferred",
    "proficiency",
    "required",
    "role",
    "skills",
    "strong",
    "the",
    "to",
    "using",
    "with",
    "work",
    "working",
    "year",
    "years",
}
TERM_ALIASES = {
    "ai": "artificialintelligence",
    "apis": "api",
    "aws": "amazonwebservices",
    "gcp": "googlecloud",
    "js": "javascript",
    "k8s": "kubernetes",
    "llm": "largelanguagemodel",
    "llms": "largelanguagemodel",
    "ml": "machinelearning",
    "postgres": "postgresql",
    "restful": "rest",
    "ts": "typescript",
}


@dataclass(frozen=True)
class _ScoredEvidence:
    evidence: EvidenceItem
    score: float
    matched_terms: tuple[str, ...]


def _term(value: str) -> str:
    normalized = value.casefold().strip(".")
    normalized = TERM_ALIASES.get(normalized, normalized)
    if len(normalized) > 4 and normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if len(normalized) > 4 and normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def _terms(value: str) -> set[str]:
    return {
        normalized
        for token in TOKEN_PATTERN.findall(value.casefold())
        if (normalized := _term(token)) and normalized not in STOP_TERMS
    }


def _eligible_evidence(profile: CandidateProfile) -> list[EvidenceItem]:
    restricted_fact_evidence = {
        evidence_id
        for fact in profile.facts
        if fact.sensitivity is not Sensitivity.ORDINARY
        or not fact.canonical_path.startswith("education.")
        for evidence_id in fact.evidence_ids
    }
    seen_statements: set[str] = set()
    eligible: list[EvidenceItem] = []
    for item in profile.evidence:
        statement = item.statement.strip()
        normalized = statement.casefold()
        if (
            not item.verified
            or item.id in restricted_fact_evidence
            or not MIN_EVIDENCE_LENGTH <= len(statement) <= MAX_EVIDENCE_LENGTH
            or CONTACT_PATTERN.search(statement)
            or SENSITIVE_EVIDENCE_PATTERN.search(statement)
            or normalized in seen_statements
        ):
            continue
        seen_statements.add(normalized)
        eligible.append(item)
    return eligible


def _score(requirement_terms: set[str], evidence: EvidenceItem) -> _ScoredEvidence | None:
    evidence_terms = _terms(evidence.statement)
    matched = requirement_terms & evidence_terms
    if not requirement_terms or not matched:
        return None
    requirement_coverage = len(matched) / len(requirement_terms)
    evidence_precision = len(matched) / max(1, min(len(evidence_terms), len(requirement_terms)))
    score = min(1.0, requirement_coverage * 0.8 + evidence_precision * 0.2)
    return _ScoredEvidence(
        evidence=evidence,
        score=round(score, 4),
        matched_terms=tuple(sorted(matched)),
    )


def _mapping(
    requirement: JobRequirement, eligible: list[EvidenceItem]
) -> RequirementEvidenceMapping:
    requirement_terms = _terms(requirement.text)
    scored = [
        match for evidence in eligible if (match := _score(requirement_terms, evidence)) is not None
    ]
    scored.sort(key=lambda item: (-item.score, str(item.evidence.id)))
    top_matches = scored[:MAX_MATCHES_PER_REQUIREMENT]
    covered_terms = {term for match in top_matches for term in match.matched_terms}
    union_coverage = len(covered_terms) / len(requirement_terms) if requirement_terms else 0
    best_score = top_matches[0].score if top_matches else 0
    confidence = round(min(1.0, union_coverage * 0.7 + best_score * 0.3), 4)
    if confidence >= 0.65:
        support = RequirementSupport.SUPPORTED
    elif confidence >= 0.25:
        support = RequirementSupport.PARTIAL
    else:
        support = RequirementSupport.UNSUPPORTED

    if top_matches:
        terms = ", ".join(sorted(covered_terms))
        explanation = (
            f"Matched {len(covered_terms)} of {len(requirement_terms)} normalized "
            f"requirement terms: {terms}."
        )
    elif not requirement_terms:
        explanation = "The requirement did not contain enough specific terms for local matching."
    else:
        explanation = "No verified candidate evidence matched this requirement."

    return RequirementEvidenceMapping(
        requirement_id=requirement.id,
        requirement_text=requirement.text,
        required=requirement.required,
        support=support,
        confidence=confidence,
        matches=[
            EvidenceMatch(
                evidence_id=match.evidence.id,
                statement=match.evidence.statement,
                source_document_id=match.evidence.source_document_id,
                source_span=match.evidence.source_span,
                score=match.score,
                matched_terms=list(match.matched_terms),
            )
            for match in top_matches
        ],
        explanation=explanation,
    )


def prepare_application_materials(
    job: JobPosting, profile: CandidateProfile
) -> ApplicationMaterialPlan:
    """Build a review-only plan from exact verified statements without a model call."""
    eligible = _eligible_evidence(profile)
    mappings = [_mapping(requirement, eligible) for requirement in job.requirements]
    supported_count = sum(mapping.support is RequirementSupport.SUPPORTED for mapping in mappings)
    partial_count = sum(mapping.support is RequirementSupport.PARTIAL for mapping in mappings)
    unsupported_count = sum(
        mapping.support is RequirementSupport.UNSUPPORTED for mapping in mappings
    )
    coverage_ratio = (
        round((supported_count + partial_count * 0.5) / len(mappings), 4) if mappings else 0
    )

    requirement_ids_by_evidence: dict[UUID, list[UUID]] = defaultdict(list)
    evidence_by_id: dict[UUID, EvidenceItem] = {}
    best_score_by_evidence: dict[UUID, float] = {}
    for mapping in mappings:
        if mapping.support is RequirementSupport.UNSUPPORTED:
            continue
        for match in mapping.matches:
            if mapping.requirement_id not in requirement_ids_by_evidence[match.evidence_id]:
                requirement_ids_by_evidence[match.evidence_id].append(mapping.requirement_id)
            best_score_by_evidence[match.evidence_id] = max(
                match.score, best_score_by_evidence.get(match.evidence_id, 0)
            )
    for item in eligible:
        evidence_by_id[item.id] = item

    ranked_ids = sorted(
        requirement_ids_by_evidence,
        key=lambda evidence_id: (-best_score_by_evidence[evidence_id], str(evidence_id)),
    )[:MAX_DRAFT_ENTRIES]
    entries = [
        GroundedResumeEntry(
            evidence_id=evidence_id,
            statement=evidence_by_id[evidence_id].statement,
            source_document_id=evidence_by_id[evidence_id].source_document_id,
            source_span=evidence_by_id[evidence_id].source_span,
            supports_requirement_ids=requirement_ids_by_evidence[evidence_id],
        )
        for evidence_id in ranked_ids
    ]

    status = MaterialPlanStatus.NEEDS_REVIEW if entries else MaterialPlanStatus.NEEDS_EVIDENCE
    return ApplicationMaterialPlan(
        job_id=job.id,
        job_version=job.version,
        candidate_profile_id=profile.id,
        candidate_profile_version=profile.version,
        status=status,
        coverage_ratio=coverage_ratio,
        supported_count=supported_count,
        partial_count=partial_count,
        unsupported_count=unsupported_count,
        mappings=mappings,
        resume_draft=GroundedResumeDraft(
            title=f"Grounded evidence draft for {job.title}", entries=entries
        ),
    )
