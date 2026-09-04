from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FactState(StrEnum):
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class DocumentStatus(StrEnum):
    PARSED = "parsed"
    NEEDS_OCR = "needs_ocr"
    FAILED = "failed"


class WorkflowState(StrEnum):
    CREATED = "created"
    INGESTING_JOB = "ingesting_job"
    PREPARING_MATERIALS = "preparing_materials"
    OPENING_APPLICATION = "opening_application"
    AUTHENTICATING = "authenticating"
    REGISTERING = "registering"
    VERIFYING_EMAIL = "verifying_email"
    FILLING = "filling"
    PAUSED = "paused"
    AWAITING_HUMAN = "awaiting_human"
    VALIDATING = "validating"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTCOME_UNCERTAIN = "outcome_uncertain"


class Platform(StrEnum):
    SYNTHETIC = "synthetic"
    WORKDAY = "workday"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    ORDINARY = "ordinary"
    SENSITIVE = "sensitive"
    LEGAL = "legal"
    DEMOGRAPHIC = "demographic"


class MappingDecision(StrEnum):
    AUTO_FILL = "auto_fill"
    REVIEW = "review"
    HUMAN_REQUIRED = "human_required"
    UNSUPPORTED = "unsupported"


class OutcomeType(StrEnum):
    SUBMITTED = "submitted"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
    OUTCOME_UNCERTAIN = "outcome_uncertain"


class OutcomeReasonCode(StrEnum):
    USER_CONFIRMED_SUBMITTED = "user_confirmed_submitted"
    INGESTION_FAILED = "ingestion_failed"
    EVIDENCE_MISSING = "evidence_missing"
    AUTHENTICATION_FAILED = "authentication_failed"
    REGISTRATION_FAILED = "registration_failed"
    VERIFICATION_FAILED = "verification_failed"
    MAPPING_FAILED = "mapping_failed"
    VALIDATION_FAILED = "validation_failed"
    SUBMISSION_FAILED = "submission_failed"
    PLATFORM_CHANGED = "platform_changed"
    POLICY_BLOCKED = "policy_blocked"
    USER_CANCELLED = "user_cancelled"
    USER_ABANDONED = "user_abandoned"
    CONFIRMATION_MISSING = "confirmation_missing"


class JobIngestionStatus(StrEnum):
    COMPLETE = "complete"
    NEEDS_REVIEW = "needs_review"


class RequirementSupport(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class MaterialPlanStatus(StrEnum):
    NEEDS_REVIEW = "needs_review"
    NEEDS_EVIDENCE = "needs_evidence"


class TraceContext(Contract):
    traceparent: str | None = None
    tracestate: str | None = None


class ActionMetadata(Contract):
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION
    run_id: UUID
    step_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=16)
    authorization_scope: Literal["inspect", "fill", "navigate", "upload", "submit"]
    redaction_policy: Literal["metadata_only", "pii_redacted", "sensitive"]
    trace_context: TraceContext = Field(default_factory=TraceContext)


class SourceSpan(Contract):
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @field_validator("end")
    @classmethod
    def validate_end(cls, value: int, info: Any) -> int:
        start = info.data.get("start")
        if start is not None and value <= start:
            raise ValueError("end must be greater than start")
        return value


class SourceDocument(Contract):
    id: UUID = Field(default_factory=uuid4)
    filename: str
    media_type: Literal[
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    encrypted_artifact_ref: str
    status: DocumentStatus = DocumentStatus.PARSED
    parse_error_code: str | None = None
    extracted_evidence_count: int = Field(default=0, ge=0)
    imported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceItem(Contract):
    id: UUID = Field(default_factory=uuid4)
    source_document_id: UUID | None = None
    source_span: SourceSpan | None = None
    statement: str
    extraction_method: Literal["deterministic", "model", "user"]
    confidence: float = Field(ge=0, le=1)
    verified: bool = False


class CandidateFact(Contract):
    id: UUID = Field(default_factory=uuid4)
    canonical_path: str
    value: str
    state: FactState
    evidence_ids: list[UUID] = Field(default_factory=list)
    sensitivity: Sensitivity = Sensitivity.ORDINARY


class CandidateProfile(Contract):
    id: UUID = Field(default_factory=uuid4)
    version: int = Field(default=1, ge=1)
    facts: list[CandidateFact] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)


class CandidateProfileInput(Contract):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    preferred_name: str = Field(default="", max_length=100)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(default="", max_length=50)
    city: str = Field(default="", max_length=120)
    region: str = Field(default="", max_length=120)
    country: str = Field(default="United States", max_length=120)
    postal_code: str = Field(default="", max_length=30)
    linkedin_url: AnyHttpUrl | None = None
    github_url: AnyHttpUrl | None = None
    school: str = Field(default="", max_length=200)
    degree: str = Field(default="", max_length=200)
    field_of_study: str = Field(default="", max_length=200)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    work_authorization: Literal[
        "unspecified", "authorized", "requires_sponsorship", "not_authorized"
    ] = "unspecified"
    requires_sponsorship: bool | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        local, separator, domain = value.strip().partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("Enter a complete email address")
        return value.strip()


class SaveCandidateProfileRequest(Contract):
    profile: CandidateProfileInput
    expected_version: int | None = Field(default=None, ge=1)


class CandidateProfileSnapshot(Contract):
    profile: CandidateProfile
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResumeImportResult(Contract):
    snapshot: CandidateProfileSnapshot
    document: SourceDocument


type ResumeSuggestionPath = Literal[
    "identity.first_name",
    "identity.last_name",
    "contact.email",
    "contact.phone",
    "links.linkedin",
    "links.github",
    "education.0.school",
    "education.0.degree",
    "education.0.field_of_study",
    "education.0.graduation_year",
]


class ResumeFieldSuggestion(Contract):
    canonical_path: ResumeSuggestionPath
    value: str
    confidence: float = Field(ge=0, le=1)
    source_span: SourceSpan


class ResumePreviewResult(Contract):
    status: DocumentStatus
    parse_error_code: str | None = None
    extracted_evidence_count: int = Field(ge=0)
    suggestions: list[ResumeFieldSuggestion] = Field(default_factory=list)


class SetEvidenceVerificationRequest(Contract):
    expected_version: int = Field(ge=1)
    verified: bool


class JobRequirement(Contract):
    id: UUID = Field(default_factory=uuid4)
    text: str
    required: bool
    source_span: SourceSpan


class PlatformDetection(Contract):
    platform: Platform
    confidence: float = Field(ge=0, le=1)
    signals: list[str] = Field(default_factory=list)


class JobPosting(Contract):
    id: UUID = Field(default_factory=uuid4)
    version: int = Field(default=1, ge=1)
    supersedes_id: UUID | None = None
    source_url: AnyHttpUrl
    canonical_url: AnyHttpUrl
    resolved_url: AnyHttpUrl
    title: str
    company: str
    location: str = ""
    description: str
    description_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    requirements: list[JobRequirement] = Field(default_factory=list)
    platform: PlatformDetection
    status: JobIngestionStatus
    warnings: list[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IngestJobRequest(Contract):
    url: AnyHttpUrl


class PrepareMaterialsRequest(Contract):
    job_id: UUID
    candidate_profile_id: UUID
    candidate_profile_version: int = Field(ge=1)


class EvidenceMatch(Contract):
    evidence_id: UUID
    statement: str
    source_document_id: UUID | None = None
    source_span: SourceSpan | None = None
    score: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(default_factory=list)


class RequirementEvidenceMapping(Contract):
    requirement_id: UUID
    requirement_text: str
    required: bool
    support: RequirementSupport
    confidence: float = Field(ge=0, le=1)
    matches: list[EvidenceMatch] = Field(default_factory=list)
    explanation: str


class GroundedResumeEntry(Contract):
    evidence_id: UUID
    statement: str
    source_document_id: UUID | None = None
    source_span: SourceSpan | None = None
    supports_requirement_ids: list[UUID] = Field(default_factory=list)


class GroundedResumeDraft(Contract):
    title: str
    entries: list[GroundedResumeEntry] = Field(default_factory=list)


class ApplicationMaterialPlan(Contract):
    job_id: UUID
    job_version: int = Field(ge=1)
    candidate_profile_id: UUID
    candidate_profile_version: int = Field(ge=1)
    generator_version: Literal["deterministic-v1"] = "deterministic-v1"
    status: MaterialPlanStatus
    coverage_ratio: float = Field(ge=0, le=1)
    supported_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    unsupported_count: int = Field(ge=0)
    mappings: list[RequirementEvidenceMapping] = Field(default_factory=list)
    resume_draft: GroundedResumeDraft
    model_used: Literal[False] = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FormControl(Contract):
    control_id: str
    label: str
    kind: Literal["text", "email", "tel", "select", "checkbox", "radio", "file", "textarea"]
    required: bool
    sensitivity: Sensitivity
    options: list[str] = Field(default_factory=list)
    autocomplete: str | None = None


class ObservedForm(Contract):
    page_url: AnyHttpUrl
    page_state_hash: str
    controls: list[FormControl]


class FieldMapping(Contract):
    control_id: str
    canonical_path: str | None
    source: Literal["adapter", "deterministic", "model", "user"]
    confidence: float = Field(ge=0, le=1)
    sensitivity: Sensitivity
    decision: MappingDecision
    rationale: str


class FieldExplanation(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_id: str = Field(min_length=1, max_length=128)
    page_state_hash: str = Field(min_length=1, max_length=128)
    control_id: str = Field(min_length=1, max_length=200)
    canonical_path: str | None = Field(default=None, max_length=200)
    source: Literal["adapter", "deterministic", "model", "user"]
    confidence: float = Field(ge=0, le=1)
    sensitivity: Sensitivity
    decision: MappingDecision
    rationale: str = Field(min_length=1, max_length=500)
    filled: bool
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FieldValue(Contract):
    canonical_path: str
    value: str
    evidence_ids: list[UUID]


class BrowserFieldFill(Contract):
    control_id: str = Field(min_length=1, max_length=200)
    canonical_path: str = Field(min_length=1, max_length=200)
    value: str = Field(max_length=10_000)
    evidence_ids: list[UUID]
    rationale: str = Field(min_length=1, max_length=500)


class PolicyDecision(Contract):
    allowed: bool
    decision: MappingDecision
    reason_code: str
    explanation: str


class BrowserAction(Contract):
    metadata: ActionMetadata
    action_id: UUID = Field(default_factory=uuid4)
    kind: Literal["scan", "fill", "upload", "click", "navigate", "submit"]
    control_id: str | None = None
    canonical_value_ref: str | None = None


class BrowserActionResult(Contract):
    type: Literal["action_result"] = "action_result"
    action_id: UUID
    run_id: UUID
    action: Literal[
        "navigate",
        "open_synthetic_form",
        "fill",
        "scan",
        "pause",
        "resume",
        "cancel",
    ]
    ok: bool
    page_state_hash: str | None = None
    error_code: str | None = None


class BrowserCommand(Contract):
    type: Literal["command"] = "command"
    command_id: UUID = Field(default_factory=uuid4)
    action: Literal[
        "navigate",
        "open_synthetic_form",
        "fill",
        "scan",
        "pause",
        "resume",
        "cancel",
    ]
    url: AnyHttpUrl | None = None
    browser_profile_dir: str | None = None
    expected_page_state_hash: str | None = Field(default=None, min_length=1, max_length=128)
    fills: list[BrowserFieldFill] = Field(default_factory=list)
    blocked_mappings: list[FieldMapping] = Field(default_factory=list)
    envelope: ActionMetadata


class ConfirmationEvidence(Contract):
    kind: Literal["confirmation_page", "application_id", "confirmation_email", "user_correction"]
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_ref: str | None = None


class ApplicationOutcome(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    revision: int = Field(ge=1)
    supersedes_id: UUID | None = None
    outcome: OutcomeType
    reason_code: OutcomeReasonCode
    confirmation: list[ConfirmationEvidence] = Field(default_factory=list)
    recorded_by: Literal["user"] = "user"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def require_submission_confirmation(self) -> ApplicationOutcome:
        if self.outcome is OutcomeType.SUBMITTED and not self.confirmation:
            raise ValueError("submitted outcomes require confirmation evidence")
        return self


class ApplicationRun(Contract):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    candidate_profile_id: UUID
    candidate_profile_version: int = Field(ge=1)
    job_url: AnyHttpUrl
    job_title: str | None = None
    company: str | None = None
    platform: Platform | None = None
    state: WorkflowState = WorkflowState.CREATED
    latest_outcome: ApplicationOutcome | None = None
    auto_submit_authorized: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowEvent(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    sequence: int = Field(ge=1)
    event_type: str
    from_state: WorkflowState | None = None
    to_state: WorkflowState
    reason_code: str
    safe_details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Checkpoint(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    step_id: str
    sequence: int = Field(ge=1)
    state: WorkflowState
    idempotency_key: str = Field(min_length=16)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InterventionRequest(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    category: Literal[
        "captcha",
        "two_factor",
        "oauth_consent",
        "mailbox_ambiguity",
        "legal",
        "demographic",
        "sensitive",
        "low_confidence",
        "site_change",
        "validation_conflict",
        "uncertain_side_effect",
    ]
    explanation: str
    page_state_hash: str | None = None
    expires_at: datetime | None = None


class InterventionResponse(Contract):
    intervention_id: UUID
    decision: Literal["approve_once", "correct", "retry", "reject", "cancel"]
    corrected_value_ref: str | None = None
    page_state_hash: str | None = None


class RecordApplicationOutcomeRequest(Contract):
    outcome: OutcomeType
    reason_code: OutcomeReasonCode
    confirmed_by_user: Literal[True]

    @model_validator(mode="after")
    def validate_reason_for_outcome(self) -> RecordApplicationOutcomeRequest:
        allowed: dict[OutcomeType, frozenset[OutcomeReasonCode]] = {
            OutcomeType.SUBMITTED: frozenset({OutcomeReasonCode.USER_CONFIRMED_SUBMITTED}),
            OutcomeType.FAILED: frozenset(
                {
                    OutcomeReasonCode.INGESTION_FAILED,
                    OutcomeReasonCode.EVIDENCE_MISSING,
                    OutcomeReasonCode.AUTHENTICATION_FAILED,
                    OutcomeReasonCode.REGISTRATION_FAILED,
                    OutcomeReasonCode.VERIFICATION_FAILED,
                    OutcomeReasonCode.MAPPING_FAILED,
                    OutcomeReasonCode.VALIDATION_FAILED,
                    OutcomeReasonCode.SUBMISSION_FAILED,
                    OutcomeReasonCode.PLATFORM_CHANGED,
                    OutcomeReasonCode.POLICY_BLOCKED,
                }
            ),
            OutcomeType.CANCELLED: frozenset({OutcomeReasonCode.USER_CANCELLED}),
            OutcomeType.ABANDONED: frozenset({OutcomeReasonCode.USER_ABANDONED}),
            OutcomeType.OUTCOME_UNCERTAIN: frozenset({OutcomeReasonCode.CONFIRMATION_MISSING}),
        }
        if self.reason_code not in allowed[self.outcome]:
            raise ValueError("reason_code is not valid for the selected outcome")
        return self


class ApplicationStatistics(Contract):
    total_runs: int = Field(ge=0)
    resolved_runs: int = Field(ge=0)
    pending_runs: int = Field(ge=0)
    submitted: int = Field(ge=0)
    failed: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    abandoned: int = Field(ge=0)
    outcome_uncertain: int = Field(ge=0)
    resolution_rate: float = Field(ge=0, le=1)
    submitted_rate: float = Field(ge=0, le=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelCallRecord(Contract):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    model: str
    prompt_version: str
    schema_name: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    trace_context: TraceContext


class HealthStatus(Contract):
    status: Literal["starting", "ready", "degraded", "stopped"]
    service: str = "careerflow-agent"
    version: str
    browser_worker_connected: bool
    browser_worker_session_id: UUID | None = None
    database_ready: bool
    telemetry_ready: bool


class CreateRunRequest(Contract):
    job_id: UUID
    candidate_profile_id: UUID
    candidate_profile_version: int = Field(ge=1)
    job_url: AnyHttpUrl
    auto_submit_authorized: bool = False
    start_immediately: bool = True

    @field_validator("job_url")
    @classmethod
    def reject_local_job_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        hostname = (value.host or "").lower()
        if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(
            (".localhost", ".local")
        ):
            raise ValueError("Local and private job URLs are not permitted")
        return value


class StartSyntheticDemoRequest(Contract):
    candidate_profile_id: UUID
    candidate_profile_version: int = Field(ge=1)


class RunControlRequest(Contract):
    command: Literal["pause", "resume", "cancel"]
    idempotency_key: Annotated[str, Field(min_length=16, max_length=128)]


class TransitionRequest(Contract):
    to_state: WorkflowState
    reason_code: str
    idempotency_key: Annotated[str, Field(min_length=16)]
