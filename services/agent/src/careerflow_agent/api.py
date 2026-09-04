from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import UUID

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from opentelemetry import metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import inject
from opentelemetry.trace import get_tracer
from pydantic import AnyHttpUrl

from . import __version__
from .config import Settings, get_settings
from .contracts import (
    ActionMetadata,
    ApplicationMaterialPlan,
    ApplicationOutcome,
    ApplicationRun,
    ApplicationStatistics,
    BrowserActionResult,
    BrowserCommand,
    CandidateProfileSnapshot,
    Checkpoint,
    CreateRunRequest,
    DocumentStatus,
    FieldExplanation,
    FieldMapping,
    HealthStatus,
    IngestJobRequest,
    JobIngestionStatus,
    JobPosting,
    JobRequirement,
    ObservedForm,
    OutcomeReasonCode,
    OutcomeType,
    Platform,
    PlatformDetection,
    PrepareMaterialsRequest,
    RecordApplicationOutcomeRequest,
    ResumeImportResult,
    ResumePreviewResult,
    RunControlRequest,
    SaveCandidateProfileRequest,
    SetEvidenceVerificationRequest,
    SourceSpan,
    StartSyntheticDemoRequest,
    TraceContext,
    TransitionRequest,
    WorkflowEvent,
    WorkflowState,
)
from .database import Database
from .document_parser import (
    MAX_RESUME_BYTES,
    PDF_MEDIA_TYPE,
    SUPPORTED_RESUME_MEDIA_TYPES,
    ResumeMediaType,
    ResumeParseError,
    extract_profile_suggestions,
    parse_resume,
)
from .form_mapping import plan_form_fill
from .job_ingestion import JobIngestionError, JobIngestionService
from .keychain import KeychainSecretStore, KeychainUnavailableError
from .material_preparation import prepare_application_materials
from .profile_vault import (
    EvidenceNotFoundError,
    ProfileKeyUnavailableError,
    ProfileRequiredError,
    ProfileVault,
    ProfileVersionConflictError,
    ResumeAlreadyImportedError,
    SecretStore,
)
from .telemetry import configure_telemetry
from .workflow import InvalidTransitionError, RunNotFoundError, WorkflowService

tracer = get_tracer("careerflow.agent.documents")
tracking_tracer = get_tracer("careerflow.agent.application_tracking")
tracking_meter = metrics.get_meter("careerflow.agent.application_tracking")
OUTCOME_WRITE_REQUESTS = tracking_meter.create_counter("application_outcome_write_requests_total")

SYNTHETIC_FORM_URL = "https://synthetic.careerflow.invalid/application"
SYNTHETIC_DESCRIPTION = (
    "Controlled local CareerFlow test form for deterministic scanning, policy evaluation, "
    "and supervised filling. It cannot submit data to an employer."
)


class ServiceState:
    def __init__(self, settings: Settings, secret_store: SecretStore) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.workflow = WorkflowService(self.database)
        self.job_ingestion = JobIngestionService(self.database)
        self.profile_vault = ProfileVault(self.database, secret_store, settings.data_dir)
        self.browser_worker_connected = False
        self.browser_socket: WebSocket | None = None
        self.telemetry_ready = (
            configure_telemetry(settings) if settings.telemetry_enabled else False
        )
        self.subscribers: set[asyncio.Queue[dict[str, object]]] = set()

    async def publish(self, event: dict[str, object]) -> None:
        for subscriber in self.subscribers:
            if subscriber.full():
                subscriber.get_nowait()
            subscriber.put_nowait(event)

    async def navigate_browser(self, run: ApplicationRun) -> None:
        if self.browser_socket is None:
            raise RuntimeError("Browser worker is not connected")
        carrier: dict[str, str] = {}
        inject(carrier)
        command = BrowserCommand(
            action="navigate",
            url=run.job_url,
            envelope=ActionMetadata(
                run_id=run.id,
                step_id="opening_application",
                idempotency_key=f"navigate-job-{run.id}",
                authorization_scope="navigate",
                redaction_policy="metadata_only",
                trace_context=TraceContext(traceparent=carrier.get("traceparent")),
            ),
        )
        await self.browser_socket.send_json(
            command.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    async def open_synthetic_form(self, run: ApplicationRun) -> None:
        if self.browser_socket is None:
            raise RuntimeError("Browser worker is not connected")
        carrier: dict[str, str] = {}
        inject(carrier)
        command = BrowserCommand(
            action="open_synthetic_form",
            envelope=ActionMetadata(
                run_id=run.id,
                step_id="synthetic_form_scan",
                idempotency_key=f"synthetic-form-scan-{run.id}",
                authorization_scope="inspect",
                redaction_policy="metadata_only",
                trace_context=TraceContext(traceparent=carrier.get("traceparent")),
            ),
        )
        await self.browser_socket.send_json(
            command.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    async def scan_synthetic_form(self, run: ApplicationRun, idempotency_key: str) -> None:
        if self.browser_socket is None:
            raise RuntimeError("Browser worker is not connected")
        carrier: dict[str, str] = {}
        inject(carrier)
        command = BrowserCommand(
            action="scan",
            envelope=ActionMetadata(
                run_id=run.id,
                step_id="synthetic_form_rescan",
                idempotency_key=idempotency_key,
                authorization_scope="inspect",
                redaction_policy="metadata_only",
                trace_context=TraceContext(traceparent=carrier.get("traceparent")),
            ),
        )
        await self.browser_socket.send_json(
            command.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    async def send_browser_control(self, run: ApplicationRun, request: RunControlRequest) -> None:
        if self.browser_socket is None:
            return
        carrier: dict[str, str] = {}
        inject(carrier)
        command = BrowserCommand(
            action=request.command,
            envelope=ActionMetadata(
                run_id=run.id,
                step_id=f"user_{request.command}",
                idempotency_key=request.idempotency_key,
                authorization_scope="inspect",
                redaction_policy="metadata_only",
                trace_context=TraceContext(traceparent=carrier.get("traceparent")),
            ),
        )
        await self.browser_socket.send_json(
            command.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    async def handle_observed_form(
        self, *, run_id: UUID, action_id: str, observed_form: ObservedForm
    ) -> None:
        if self.browser_socket is None:
            raise RuntimeError("Browser worker is not connected")
        run = await self.database.get_run(run_id)
        snapshot = await self.profile_vault.load()
        if run is None:
            raise RunNotFoundError(str(run_id))
        if run.state in {WorkflowState.PAUSED, WorkflowState.CANCELLED} or run.latest_outcome:
            return
        if (
            run.platform is not Platform.SYNTHETIC
            or str(observed_form.page_url) != SYNTHETIC_FORM_URL
        ):
            await self.workflow.transition(
                run_id=run_id,
                to_state=WorkflowState.AWAITING_HUMAN,
                reason_code="unexpected_form_observation",
                idempotency_key=f"unexpected-form-{action_id}",
            )
            return
        if (
            snapshot is None
            or snapshot.profile.id != run.candidate_profile_id
            or snapshot.profile.version != run.candidate_profile_version
        ):
            await self.workflow.transition(
                run_id=run_id,
                to_state=WorkflowState.AWAITING_HUMAN,
                reason_code="profile_version_changed_before_fill",
                idempotency_key=f"synthetic-profile-stale-{action_id}",
            )
            return

        fills, mappings, blocked = plan_form_fill(observed_form, snapshot.profile)
        await self.database.save_field_explanations(
            run_id=run_id,
            step_id="synthetic_form_fill",
            page_state_hash=observed_form.page_state_hash,
            mappings=mappings,
            filled_control_ids=set(),
        )
        await self.workflow.transition(
            run_id=run_id,
            to_state=WorkflowState.FILLING,
            reason_code="synthetic_form_scanned",
            idempotency_key=f"synthetic-scan-result-{action_id}",
            safe_details={
                "observed_control_count": len(observed_form.controls),
                "approved_fill_count": len(fills),
                "review_required_count": len(blocked),
            },
        )
        carrier: dict[str, str] = {}
        inject(carrier)
        command = BrowserCommand(
            action="fill",
            expected_page_state_hash=observed_form.page_state_hash,
            fills=fills,
            blocked_mappings=blocked,
            envelope=ActionMetadata(
                run_id=run_id,
                step_id="synthetic_form_fill",
                idempotency_key=f"synthetic-form-fill-{run_id}",
                authorization_scope="fill",
                redaction_policy="sensitive",
                trace_context=TraceContext(traceparent=carrier.get("traceparent")),
            ),
        )
        await self.browser_socket.send_json(
            command.model_dump(mode="json", by_alias=True, exclude_none=True)
        )

    async def handle_fill_result(
        self,
        *,
        run_id: UUID,
        action_id: str,
        ok: bool,
        page_state_hash: str | None,
        filled_mappings: list[FieldMapping],
        blocked_mappings: list[FieldMapping],
    ) -> None:
        run = await self.database.get_run(run_id)
        if run is None:
            raise RunNotFoundError(str(run_id))
        if run.state in {WorkflowState.PAUSED, WorkflowState.CANCELLED} or run.latest_outcome:
            return
        if run.platform is not Platform.SYNTHETIC:
            raise InvalidTransitionError("Synthetic fill results require a synthetic run")
        filled_count = len(filled_mappings)
        blocked_count = len(blocked_mappings)
        if page_state_hash:
            await self.database.save_field_explanations(
                run_id=run_id,
                step_id="synthetic_form_fill",
                page_state_hash=page_state_hash,
                mappings=[*filled_mappings, *blocked_mappings],
                filled_control_ids={mapping.control_id for mapping in filled_mappings},
            )
        if not ok:
            await self.workflow.transition(
                run_id=run_id,
                to_state=WorkflowState.AWAITING_HUMAN,
                reason_code="synthetic_form_fill_failed",
                idempotency_key=f"synthetic-fill-failed-{action_id}",
            )
            return
        await self.workflow.transition(
            run_id=run_id,
            to_state=WorkflowState.VALIDATING,
            reason_code="synthetic_form_fill_complete",
            idempotency_key=f"synthetic-fill-result-{action_id}",
            safe_details={
                "filled_control_count": filled_count,
                "review_required_count": blocked_count,
            },
        )
        await self.workflow.transition(
            run_id=run_id,
            to_state=(
                WorkflowState.AWAITING_HUMAN if blocked_count else WorkflowState.READY_TO_SUBMIT
            ),
            reason_code=(
                "synthetic_form_review_required" if blocked_count else "synthetic_form_validated"
            ),
            idempotency_key=f"synthetic-review-result-{action_id}",
            safe_details={"review_required_count": blocked_count},
        )


def create_app(
    settings: Settings | None = None, secret_store: SecretStore | None = None
) -> FastAPI:
    configured = settings or get_settings()
    state = ServiceState(configured, secret_store or KeychainSecretStore())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await state.database.initialize()
        if configured.telemetry_enabled:
            SQLAlchemyInstrumentor().instrument(engine=state.database.engine.sync_engine)
        yield
        await state.database.close()

    app = FastAPI(
        title="CareerFlow Local API",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.state.service = state
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=[],
        allow_headers=[],
    )

    def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
        expected = configured.local_token.get_secret_value()
        if not expected or not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        if not hmac.compare_digest(authorization.removeprefix("Bearer "), expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.get("/v1/health", response_model=HealthStatus)
    async def health(_auth: None = Depends(require_token)) -> HealthStatus:
        ready = state.database.ready and state.browser_worker_connected
        return HealthStatus(
            status="ready" if ready else "starting",
            version=__version__,
            browser_worker_connected=state.browser_worker_connected,
            database_ready=state.database.ready,
            telemetry_ready=state.telemetry_ready,
        )

    @app.get("/v1/profile", response_model=CandidateProfileSnapshot | None)
    async def get_profile(
        _auth: None = Depends(require_token),
    ) -> CandidateProfileSnapshot | None:
        try:
            return await state.profile_vault.load()
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.put("/v1/profile", response_model=CandidateProfileSnapshot)
    async def save_profile(
        request: SaveCandidateProfileRequest,
        _auth: None = Depends(require_token),
    ) -> CandidateProfileSnapshot:
        try:
            return await state.profile_vault.save(
                request.profile, expected_version=request.expected_version
            )
        except ProfileVersionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/v1/profile/resume", response_model=ResumeImportResult, status_code=201)
    async def import_resume(
        file: Annotated[UploadFile, File()],
        expected_version: Annotated[int, Form(ge=1)],
        _auth: None = Depends(require_token),
    ) -> ResumeImportResult:
        media_type = file.content_type or ""
        if media_type not in SUPPORTED_RESUME_MEDIA_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Choose a PDF or DOCX résumé",
            )
        content = await file.read(MAX_RESUME_BYTES + 1)
        if not content:
            raise HTTPException(status_code=422, detail="The résumé file is empty")
        if len(content) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail="Résumé files must be 10 MB or smaller")
        filename = file.filename or "resume"
        try:
            with tracer.start_as_current_span("document.parse") as span:
                span.set_attribute("document.media_type", media_type)
                result = await state.profile_vault.import_resume(
                    content,
                    filename=filename,
                    media_type=cast(ResumeMediaType, media_type),
                    expected_version=expected_version,
                )
                span.set_attribute("document.status", result.document.status)
                span.set_attribute(
                    "document.evidence_count", result.document.extracted_evidence_count
                )
                return result
        except ProfileVersionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ResumeAlreadyImportedError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ProfileRequiredError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/v1/profile/resume/preview", response_model=ResumePreviewResult)
    async def preview_resume(
        file: Annotated[UploadFile, File()],
        _auth: None = Depends(require_token),
    ) -> ResumePreviewResult:
        media_type = file.content_type or ""
        if media_type not in SUPPORTED_RESUME_MEDIA_TYPES:
            raise HTTPException(status_code=415, detail="Choose a PDF or DOCX résumé")
        content = await file.read(MAX_RESUME_BYTES + 1)
        if not content:
            raise HTTPException(status_code=422, detail="The résumé file is empty")
        if len(content) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail="Résumé files must be 10 MB or smaller")
        try:
            with tracer.start_as_current_span("document.preview") as span:
                span.set_attribute("document.media_type", media_type)
                statements = parse_resume(content, cast(ResumeMediaType, media_type))
                status_value = (
                    DocumentStatus.PARSED
                    if statements
                    else DocumentStatus.NEEDS_OCR
                    if media_type == PDF_MEDIA_TYPE
                    else DocumentStatus.FAILED
                )
                error_code = None if statements else "selectable_text_unavailable"
                suggestions = extract_profile_suggestions(statements)
                span.set_attribute("document.status", status_value)
                span.set_attribute("document.evidence_count", len(statements))
                span.set_attribute("document.suggestion_count", len(suggestions))
                return ResumePreviewResult(
                    status=status_value,
                    parse_error_code=error_code,
                    extracted_evidence_count=len(statements),
                    suggestions=suggestions,
                )
        except ResumeParseError as error:
            return ResumePreviewResult(
                status=DocumentStatus.FAILED,
                parse_error_code=error.error_code,
                extracted_evidence_count=0,
            )

    @app.put(
        "/v1/profile/evidence/{evidence_id}/verification",
        response_model=CandidateProfileSnapshot,
    )
    async def set_evidence_verification(
        evidence_id: UUID,
        request: SetEvidenceVerificationRequest,
        _auth: None = Depends(require_token),
    ) -> CandidateProfileSnapshot:
        try:
            return await state.profile_vault.set_evidence_verification(
                evidence_id,
                verified=request.verified,
                expected_version=request.expected_version,
            )
        except ProfileVersionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (ProfileRequiredError, EvidenceNotFoundError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/v1/jobs/ingest", response_model=JobPosting)
    async def ingest_job(
        request: IngestJobRequest,
        _auth: None = Depends(require_token),
    ) -> JobPosting:
        try:
            with tracer.start_as_current_span("job.ingest") as span:
                result = await state.job_ingestion.ingest(str(request.url))
                span.set_attribute("job.id", str(result.id))
                span.set_attribute("job.platform", result.platform.platform)
                span.set_attribute("job.status", result.status)
                span.set_attribute("job.requirement_count", len(result.requirements))
                return result
        except JobIngestionError as error:
            status_code = 422 if error.code in {"invalid_url", "unsafe_url"} else 502
            raise HTTPException(
                status_code=status_code,
                detail={"code": error.code, "message": str(error)},
            ) from error

    @app.get("/v1/jobs/{job_id}", response_model=JobPosting)
    async def get_job(
        job_id: UUID,
        _auth: None = Depends(require_token),
    ) -> JobPosting:
        posting = await state.database.get_job_posting(job_id)
        if posting is None:
            raise HTTPException(status_code=404, detail="Job posting not found")
        return posting

    @app.post("/v1/materials/prepare", response_model=ApplicationMaterialPlan)
    async def prepare_materials(
        request: PrepareMaterialsRequest,
        _auth: None = Depends(require_token),
    ) -> ApplicationMaterialPlan:
        job = await state.database.get_job_posting(request.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job posting not found")
        try:
            snapshot = await state.profile_vault.load()
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        if snapshot is None:
            raise HTTPException(status_code=422, detail="Create a verified profile first")
        if (
            snapshot.profile.id != request.candidate_profile_id
            or snapshot.profile.version != request.candidate_profile_version
        ):
            raise HTTPException(
                status_code=409,
                detail="The selected candidate profile version is no longer current",
            )

        with tracer.start_as_current_span("materials.prepare") as span:
            result = prepare_application_materials(job, snapshot.profile)
            span.set_attribute("materials.generator_version", result.generator_version)
            span.set_attribute("materials.requirement_count", len(result.mappings))
            span.set_attribute("materials.supported_count", result.supported_count)
            span.set_attribute("materials.partial_count", result.partial_count)
            span.set_attribute("materials.unsupported_count", result.unsupported_count)
            span.set_attribute("materials.draft_entry_count", len(result.resume_draft.entries))
            span.set_attribute("materials.model_used", result.model_used)
            return result

    @app.post("/v1/runs", response_model=ApplicationRun, status_code=201)
    async def create_run(
        request: CreateRunRequest, _auth: None = Depends(require_token)
    ) -> ApplicationRun:
        run = await state.database.create_run(request)
        if request.start_immediately and state.browser_socket is not None:
            for next_state, reason in (
                (WorkflowState.INGESTING_JOB, "job_review_confirmed"),
                (WorkflowState.PREPARING_MATERIALS, "normalized_job_attached"),
                (WorkflowState.OPENING_APPLICATION, "browser_navigation_requested"),
            ):
                await state.workflow.transition(
                    run_id=run.id,
                    to_state=next_state,
                    reason_code=reason,
                    idempotency_key=f"foundation-{next_state}-{run.id}",
                )
            run.state = WorkflowState.OPENING_APPLICATION
            await state.navigate_browser(run)
        await state.publish({"type": "run_created", "run_id": str(run.id), "state": run.state})
        return run

    @app.get("/v1/runs", response_model=list[ApplicationRun])
    async def list_runs(_auth: None = Depends(require_token)) -> list[ApplicationRun]:
        return await state.database.list_runs()

    @app.post("/v1/demo/synthetic-run", response_model=ApplicationRun, status_code=201)
    async def start_synthetic_run(
        request: StartSyntheticDemoRequest,
        _auth: None = Depends(require_token),
    ) -> ApplicationRun:
        if state.browser_socket is None:
            raise HTTPException(status_code=503, detail="Browser worker is not connected")
        try:
            snapshot = await state.profile_vault.load()
        except (KeychainUnavailableError, ProfileKeyUnavailableError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        if snapshot is None:
            raise HTTPException(status_code=422, detail="Create a verified profile first")
        if (
            snapshot.profile.id != request.candidate_profile_id
            or snapshot.profile.version != request.candidate_profile_version
        ):
            raise HTTPException(status_code=409, detail="The candidate profile version changed")

        job = await state.database.save_job_posting(
            JobPosting(
                source_url=AnyHttpUrl(SYNTHETIC_FORM_URL),
                canonical_url=AnyHttpUrl(SYNTHETIC_FORM_URL),
                resolved_url=AnyHttpUrl(SYNTHETIC_FORM_URL),
                title="Safe Autofill Lab",
                company="CareerFlow Synthetic ATS",
                description=SYNTHETIC_DESCRIPTION,
                description_hash=hashlib.sha256(SYNTHETIC_DESCRIPTION.encode()).hexdigest(),
                requirements=[
                    JobRequirement(
                        text="Test deterministic profile-field mapping without submission.",
                        required=True,
                        source_span=SourceSpan(
                            section="synthetic-fixture",
                            start=0,
                            end=len(SYNTHETIC_DESCRIPTION),
                        ),
                    )
                ],
                platform=PlatformDetection(
                    platform=Platform.SYNTHETIC,
                    confidence=1,
                    signals=["app-owned-fixture"],
                ),
                status=JobIngestionStatus.COMPLETE,
            )
        )
        run = await state.database.create_run(
            CreateRunRequest(
                job_id=job.id,
                candidate_profile_id=snapshot.profile.id,
                candidate_profile_version=snapshot.profile.version,
                job_url=AnyHttpUrl(SYNTHETIC_FORM_URL),
                auto_submit_authorized=False,
                start_immediately=False,
            )
        )
        for next_state, reason in (
            (WorkflowState.INGESTING_JOB, "synthetic_fixture_selected"),
            (WorkflowState.PREPARING_MATERIALS, "synthetic_profile_attached"),
            (WorkflowState.OPENING_APPLICATION, "synthetic_form_scan_requested"),
        ):
            await state.workflow.transition(
                run_id=run.id,
                to_state=next_state,
                reason_code=reason,
                idempotency_key=f"synthetic-{next_state}-{run.id}",
            )
        run.state = WorkflowState.OPENING_APPLICATION
        await state.open_synthetic_form(run)
        await state.publish({"type": "run_created", "run_id": str(run.id), "state": run.state})
        return run

    @app.post("/v1/runs/{run_id}/transitions", response_model=WorkflowEvent)
    async def transition_run(
        run_id: UUID,
        request: TransitionRequest,
        _auth: None = Depends(require_token),
    ) -> WorkflowEvent:
        try:
            event = await state.workflow.transition(
                run_id=run_id,
                to_state=request.to_state,
                reason_code=request.reason_code,
                idempotency_key=request.idempotency_key,
            )
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="Run not found") from error
        except InvalidTransitionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        await state.publish(
            {"type": "workflow_transition", "run_id": str(run_id), "state": event.to_state}
        )
        return event

    @app.post("/v1/runs/{run_id}/control", response_model=ApplicationRun)
    async def control_run(
        run_id: UUID,
        request: RunControlRequest,
        _auth: None = Depends(require_token),
    ) -> ApplicationRun:
        run = await state.database.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        existing = await state.database.get_event_by_idempotency(run_id, request.idempotency_key)
        if existing:
            current = await state.database.get_run(run_id)
            if current is None:
                raise HTTPException(status_code=404, detail="Run not found")
            return current
        if run.latest_outcome:
            raise HTTPException(
                status_code=409, detail="Completed applications cannot be controlled"
            )

        try:
            if request.command == "pause":
                if run.state in {
                    WorkflowState.PAUSED,
                    WorkflowState.SUBMITTING,
                    WorkflowState.SUBMITTED,
                    WorkflowState.FAILED,
                    WorkflowState.CANCELLED,
                    WorkflowState.OUTCOME_UNCERTAIN,
                }:
                    raise InvalidTransitionError(f"Cannot pause a run in {run.state}")
                await state.database.save_checkpoint(
                    run_id=run_id,
                    step_id="user_pause",
                    state=run.state,
                    idempotency_key=request.idempotency_key,
                )
                await state.workflow.transition(
                    run_id=run_id,
                    to_state=WorkflowState.PAUSED,
                    reason_code="user_requested_pause",
                    idempotency_key=request.idempotency_key,
                    safe_details={"checkpoint_state": run.state},
                )
            elif request.command == "resume":
                if run.state is not WorkflowState.PAUSED:
                    raise InvalidTransitionError("Only a paused run can be resumed")
                if state.browser_socket is None:
                    raise InvalidTransitionError("Browser worker must be connected to resume")
                checkpoint = await state.database.latest_checkpoint(run_id)
                if checkpoint is None:
                    raise InvalidTransitionError("No safe checkpoint is available for this run")
                await state.workflow.transition(
                    run_id=run_id,
                    to_state=checkpoint.state,
                    reason_code="user_resumed_from_checkpoint",
                    idempotency_key=request.idempotency_key,
                    safe_details={
                        "checkpoint_id": str(checkpoint.id),
                        "checkpoint_sequence": checkpoint.sequence,
                    },
                )
            else:
                await state.workflow.transition(
                    run_id=run_id,
                    to_state=WorkflowState.CANCELLED,
                    reason_code="user_cancelled_run",
                    idempotency_key=request.idempotency_key,
                )
                await state.database.record_application_outcome(
                    run_id=run_id,
                    outcome=OutcomeType.CANCELLED,
                    reason_code=OutcomeReasonCode.USER_CANCELLED,
                )
        except (InvalidTransitionError, LookupError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

        updated = await state.database.get_run(run_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Run not found")
        await state.send_browser_control(updated, request)
        await state.publish(
            {
                "type": "run_controlled",
                "run_id": str(run_id),
                "command": request.command,
                "state": updated.state,
            }
        )
        return updated

    @app.get("/v1/runs/{run_id}/events", response_model=list[WorkflowEvent])
    async def list_run_events(
        run_id: UUID, _auth: None = Depends(require_token)
    ) -> list[WorkflowEvent]:
        return await state.database.list_events(run_id)

    @app.get("/v1/runs/{run_id}/checkpoint", response_model=Checkpoint | None)
    async def get_latest_checkpoint(
        run_id: UUID, _auth: None = Depends(require_token)
    ) -> Checkpoint | None:
        if await state.database.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return await state.database.latest_checkpoint(run_id)

    @app.get(
        "/v1/runs/{run_id}/field-explanations",
        response_model=list[FieldExplanation],
    )
    async def list_field_explanations(
        run_id: UUID, _auth: None = Depends(require_token)
    ) -> list[FieldExplanation]:
        if await state.database.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return await state.database.list_field_explanations(run_id)

    @app.put("/v1/runs/{run_id}/outcome", response_model=ApplicationOutcome)
    async def record_application_outcome(
        run_id: UUID,
        request: RecordApplicationOutcomeRequest,
        _auth: None = Depends(require_token),
    ) -> ApplicationOutcome:
        with tracking_tracer.start_as_current_span("application.outcome.record") as span:
            span.set_attribute("careerflow.run_id", str(run_id))
            span.set_attribute("careerflow.outcome", request.outcome)
            span.set_attribute("careerflow.outcome_reason", request.reason_code)
            outcome = await state.database.record_application_outcome(
                run_id=run_id,
                outcome=request.outcome,
                reason_code=request.reason_code,
            )
            if outcome is None:
                raise HTTPException(status_code=404, detail="Run not found")
            OUTCOME_WRITE_REQUESTS.add(
                1,
                {
                    "outcome": request.outcome,
                    "reason_code": request.reason_code,
                },
            )
            await state.publish(
                {
                    "type": "application_outcome_recorded",
                    "run_id": str(run_id),
                    "outcome": request.outcome,
                }
            )
            return outcome

    @app.get("/v1/runs/{run_id}/outcomes", response_model=list[ApplicationOutcome])
    async def list_application_outcomes(
        run_id: UUID,
        _auth: None = Depends(require_token),
    ) -> list[ApplicationOutcome]:
        if await state.database.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return await state.database.list_application_outcomes(run_id)

    @app.get("/v1/application-statistics", response_model=ApplicationStatistics)
    async def application_statistics(
        _auth: None = Depends(require_token),
    ) -> ApplicationStatistics:
        return await state.database.application_statistics()

    @app.get("/v1/events")
    async def events(request: Request, _auth: None = Depends(require_token)) -> StreamingResponse:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=100)
        state.subscribers.add(queue)

        async def stream() -> AsyncIterator[str]:
            try:
                while not await request.is_disconnected():
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        yield f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
                    except TimeoutError:
                        yield ": keepalive\n\n"
            finally:
                state.subscribers.discard(queue)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.websocket("/v1/browser/ws")
    async def browser_websocket(websocket: WebSocket) -> None:
        authorization = websocket.headers.get("authorization", "")
        expected = configured.local_token.get_secret_value()
        supplied = authorization.removeprefix("Bearer ")
        if not expected or not hmac.compare_digest(supplied, expected):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        state.browser_socket = websocket
        state.browser_worker_connected = True
        await state.publish({"type": "browser_worker", "connected": True})
        try:
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "ready":
                    await state.publish({"type": "browser_worker_ready"})
                elif message.get("type") == "form_observed":
                    run_id = UUID(str(message["runId"]))
                    await state.handle_observed_form(
                        run_id=run_id,
                        action_id=str(message["actionId"]),
                        observed_form=ObservedForm.model_validate(message["observedForm"]),
                    )
                    await state.publish({"type": "browser_form_observed", "run_id": str(run_id)})
                elif message.get("type") == "fill_result":
                    run_id = UUID(str(message["runId"]))
                    filled_mappings = [
                        FieldMapping.model_validate(item)
                        for item in message.get("filledMappings", [])
                    ]
                    blocked_mappings = [
                        FieldMapping.model_validate(item)
                        for item in message.get("blockedMappings", [])
                    ]
                    await state.handle_fill_result(
                        run_id=run_id,
                        action_id=str(message["actionId"]),
                        ok=bool(message.get("ok")),
                        page_state_hash=message.get("pageStateHash"),
                        filled_mappings=filled_mappings,
                        blocked_mappings=blocked_mappings,
                    )
                    await state.publish(
                        {
                            "type": "browser_fill_result",
                            "run_id": str(run_id),
                            "ok": bool(message.get("ok")),
                        }
                    )
                elif message.get("type") == "action_result":
                    result = BrowserActionResult.model_validate(message)
                    run_id = result.run_id
                    action_id = str(result.action_id)
                    if result.action in {"pause", "resume", "cancel"}:
                        run = await state.database.get_run(run_id)
                        if (
                            result.action == "resume"
                            and result.ok
                            and run
                            and run.platform is Platform.SYNTHETIC
                            and run.state not in {WorkflowState.PAUSED, WorkflowState.CANCELLED}
                            and run.latest_outcome is None
                        ):
                            await state.scan_synthetic_form(
                                run, f"synthetic-rescan-after-resume-{action_id}"
                            )
                        elif (
                            result.action == "resume"
                            and not result.ok
                            and run
                            and run.state
                            not in {
                                WorkflowState.PAUSED,
                                WorkflowState.CANCELLED,
                                WorkflowState.SUBMITTED,
                                WorkflowState.FAILED,
                                WorkflowState.OUTCOME_UNCERTAIN,
                            }
                        ):
                            await state.workflow.transition(
                                run_id=run_id,
                                to_state=WorkflowState.PAUSED,
                                reason_code="browser_resume_failed",
                                idempotency_key=f"browser-control-failed-{action_id}",
                            )
                    else:
                        run = await state.database.get_run(run_id)
                        if (
                            run
                            and run.state not in {WorkflowState.PAUSED, WorkflowState.CANCELLED}
                            and run.latest_outcome is None
                        ):
                            await state.workflow.transition(
                                run_id=run_id,
                                to_state=(
                                    WorkflowState.FILLING
                                    if result.action == "navigate" and result.ok
                                    else WorkflowState.AWAITING_HUMAN
                                ),
                                reason_code=(
                                    "browser_navigation_complete"
                                    if result.action == "navigate" and result.ok
                                    else f"browser_{result.action}_failed"
                                ),
                                idempotency_key=f"browser-result-{action_id}",
                            )
                    await state.publish(
                        {
                            "type": "browser_action_result",
                            "run_id": str(run_id),
                            "action": result.action,
                            "ok": result.ok,
                        }
                    )
        except WebSocketDisconnect:
            pass
        finally:
            state.browser_worker_connected = False
            state.browser_socket = None
            await state.publish({"type": "browser_worker", "connected": False})

    if configured.telemetry_enabled:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/v1/health",
            http_capture_headers_server_request=[],
            http_capture_headers_server_response=[],
        )
    return app
