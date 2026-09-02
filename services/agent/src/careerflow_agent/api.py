from __future__ import annotations

import asyncio
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
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagate import inject
from opentelemetry.trace import get_tracer

from . import __version__
from .config import Settings, get_settings
from .contracts import (
    ActionMetadata,
    ApplicationRun,
    BrowserCommand,
    CandidateProfileSnapshot,
    CreateRunRequest,
    HealthStatus,
    ResumeImportResult,
    SaveCandidateProfileRequest,
    SetEvidenceVerificationRequest,
    TraceContext,
    TransitionRequest,
    WorkflowEvent,
    WorkflowState,
)
from .database import Database
from .document_parser import MAX_RESUME_BYTES, SUPPORTED_RESUME_MEDIA_TYPES, ResumeMediaType
from .keychain import KeychainSecretStore, KeychainUnavailableError
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


class ServiceState:
    def __init__(self, settings: Settings, secret_store: SecretStore) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.workflow = WorkflowService(self.database)
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

    @app.post("/v1/runs", response_model=ApplicationRun, status_code=201)
    async def create_run(
        request: CreateRunRequest, _auth: None = Depends(require_token)
    ) -> ApplicationRun:
        run = await state.database.create_run(request)
        if request.start_immediately and state.browser_socket is not None:
            for next_state, reason in (
                (WorkflowState.INGESTING_JOB, "job_url_received"),
                (WorkflowState.PREPARING_MATERIALS, "foundation_materials_placeholder"),
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

    @app.get("/v1/runs/{run_id}/events", response_model=list[WorkflowEvent])
    async def list_run_events(
        run_id: UUID, _auth: None = Depends(require_token)
    ) -> list[WorkflowEvent]:
        return await state.database.list_events(run_id)

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
                elif message.get("type") == "action_result":
                    run_id = UUID(str(message["runId"]))
                    action_id = str(message["actionId"])
                    await state.workflow.transition(
                        run_id=run_id,
                        to_state=(
                            WorkflowState.FILLING
                            if message.get("ok")
                            else WorkflowState.AWAITING_HUMAN
                        ),
                        reason_code=(
                            "browser_navigation_complete"
                            if message.get("ok")
                            else "browser_navigation_failed"
                        ),
                        idempotency_key=f"browser-result-{action_id}",
                    )
                    await state.publish(
                        {
                            "type": "browser_action_result",
                            "run_id": str(run_id),
                            "ok": bool(message.get("ok")),
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
