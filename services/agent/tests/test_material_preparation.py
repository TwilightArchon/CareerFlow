from __future__ import annotations

import hashlib

from careerflow_agent.contracts import (
    CandidateFact,
    CandidateProfile,
    EvidenceItem,
    FactState,
    JobPosting,
    JobRequirement,
    PlatformDetection,
    Sensitivity,
    SourceSpan,
)
from careerflow_agent.material_preparation import prepare_application_materials


def job_posting() -> JobPosting:
    description = "Build APIs. Operate clusters."
    return JobPosting(
        source_url="https://example.com/jobs/1",
        canonical_url="https://example.com/jobs/1",
        resolved_url="https://example.com/jobs/1",
        title="Software Engineer",
        company="Example Company",
        description=description,
        description_hash=hashlib.sha256(description.encode()).hexdigest(),
        requirements=[
            JobRequirement(
                text="Build production Python REST APIs with FastAPI.",
                required=True,
                source_span=SourceSpan(start=0, end=10),
            ),
            JobRequirement(
                text="Operate Kubernetes clusters.",
                required=False,
                source_span=SourceSpan(start=11, end=20),
            ),
            JobRequirement(
                text="Must be authorized to work without sponsorship.",
                required=True,
                source_span=SourceSpan(start=21, end=30),
            ),
        ],
        platform=PlatformDetection(platform="synthetic", confidence=1),
        status="complete",
    )


def candidate_profile() -> tuple[CandidateProfile, EvidenceItem]:
    supported = EvidenceItem(
        statement="Built production Python REST APIs with FastAPI.",
        extraction_method="deterministic",
        confidence=1,
        verified=True,
        source_span=SourceSpan(page=1, section="Experience", start=0, end=48),
    )
    unverified = EvidenceItem(
        statement="Operated Kubernetes clusters.",
        extraction_method="deterministic",
        confidence=1,
        verified=False,
        source_span=SourceSpan(page=1, section="Skills", start=49, end=79),
    )
    legal = EvidenceItem(
        statement="work_authorization.status = authorized",
        extraction_method="user",
        confidence=1,
        verified=True,
    )
    contact = EvidenceItem(
        statement="synthetic.candidate@example.com",
        extraction_method="deterministic",
        confidence=1,
        verified=True,
    )
    imported_legal = EvidenceItem(
        statement="Authorized to work without sponsorship.",
        extraction_method="deterministic",
        confidence=1,
        verified=True,
    )
    profile = CandidateProfile(
        evidence=[supported, unverified, legal, contact, imported_legal],
        facts=[
            CandidateFact(
                canonical_path="work_authorization.status",
                value="authorized",
                state=FactState.VERIFIED,
                evidence_ids=[legal.id],
                sensitivity=Sensitivity.LEGAL,
            )
        ],
    )
    return profile, supported


def test_material_plan_uses_only_verified_grounded_evidence() -> None:
    profile, supported = candidate_profile()
    plan = prepare_application_materials(job_posting(), profile)

    assert plan.status == "needs_review"
    assert plan.model_used is False
    assert plan.supported_count == 1
    assert plan.partial_count == 0
    assert plan.unsupported_count == 2
    assert plan.coverage_ratio == 0.3333
    assert plan.mappings[0].support == "supported"
    assert [match.evidence_id for match in plan.mappings[0].matches] == [supported.id]
    assert plan.mappings[1].support == "unsupported"
    assert plan.mappings[1].matches == []
    assert plan.mappings[2].support == "unsupported"
    assert plan.mappings[2].matches == []
    assert [entry.statement for entry in plan.resume_draft.entries] == [supported.statement]
    assert plan.resume_draft.entries[0].evidence_id == supported.id


def test_material_plan_requires_verified_evidence() -> None:
    profile = CandidateProfile(
        evidence=[
            EvidenceItem(
                statement="Built production Python REST APIs with FastAPI.",
                extraction_method="deterministic",
                confidence=1,
                verified=False,
            )
        ]
    )

    plan = prepare_application_materials(job_posting(), profile)

    assert plan.status == "needs_evidence"
    assert plan.supported_count == 0
    assert plan.resume_draft.entries == []
