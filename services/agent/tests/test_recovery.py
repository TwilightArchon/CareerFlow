from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import AnyHttpUrl

from careerflow_agent.api import create_app
from careerflow_agent.config import Settings
from careerflow_agent.contracts import ApplicationRun, Platform, WorkflowState
from careerflow_agent.recovery import RecoveryAction, classify_recovery


def make_run(state: WorkflowState, platform: Platform | None = Platform.WORKDAY) -> ApplicationRun:
    return ApplicationRun(
        job_id=uuid4(),
        candidate_profile_id=uuid4(),
        candidate_profile_version=1,
        job_url=AnyHttpUrl("https://example.com/jobs/recovery"),
        platform=platform,
        state=state,
    )


def test_recovery_replays_only_safe_browser_work() -> None:
    assert classify_recovery(make_run(WorkflowState.OPENING_APPLICATION)) is (
        RecoveryAction.REPLAY_NAVIGATION
    )
    assert classify_recovery(make_run(WorkflowState.FILLING)) is (RecoveryAction.REPLAY_NAVIGATION)
    assert (
        classify_recovery(make_run(WorkflowState.AWAITING_HUMAN, Platform.SYNTHETIC))
        is RecoveryAction.REPLAY_SYNTHETIC_FORM
    )
    assert classify_recovery(make_run(WorkflowState.PAUSED)) is RecoveryAction.REAPPLY_PAUSE


def test_recovery_fails_closed_around_external_side_effects() -> None:
    assert classify_recovery(make_run(WorkflowState.REGISTERING)) is (
        RecoveryAction.PAUSE_FOR_REVIEW
    )
    assert classify_recovery(make_run(WorkflowState.READY_TO_SUBMIT)) is (
        RecoveryAction.PAUSE_FOR_REVIEW
    )
    assert classify_recovery(make_run(WorkflowState.SUBMITTING)) is (
        RecoveryAction.MARK_OUTCOME_UNCERTAIN
    )
    assert classify_recovery(make_run(WorkflowState.CANCELLED)) is RecoveryAction.IGNORE


async def test_safe_recovery_uses_durable_state_after_service_restart(tmp_path: Path) -> None:
    class MemorySecretStore:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def put(self, reference: str, value: str) -> None:
            self.values[reference] = value

        def get(self, reference: str) -> str | None:
            return self.values.get(reference)

        def delete(self, reference: str) -> None:
            self.values.pop(reference, None)

    class BrowserSocket:
        def __init__(self) -> None:
            self.messages: list[dict[str, object]] = []

        async def send_json(self, message: dict[str, object]) -> None:
            self.messages.append(message)

    settings = Settings(
        local_token="synthetic-recovery-token-with-32-characters",
        data_dir=tmp_path,
        telemetry_enabled=False,
    )
    secret_store = MemorySecretStore()

    @asynccontextmanager
    async def app_client() -> AsyncIterator[tuple[httpx.AsyncClient, object]]:
        app = create_app(settings, secret_store=secret_store)
        transport = httpx.ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
                headers={"Authorization": f"Bearer {settings.local_token.get_secret_value()}"},
            ) as client,
        ):
            yield client, app

    async with app_client() as (client, _app):
        created = await client.post(
            "/v1/runs",
            json={
                "job_id": str(uuid4()),
                "candidate_profile_id": str(uuid4()),
                "candidate_profile_version": 1,
                "job_url": "https://example.com/jobs/restart",
                "start_immediately": False,
            },
        )
        run_id = str(created.json()["id"])
        for sequence, state_name in enumerate(
            ["ingesting_job", "preparing_materials", "opening_application", "filling"]
        ):
            transitioned = await client.post(
                f"/v1/runs/{run_id}/transitions",
                json={
                    "to_state": state_name,
                    "reason_code": "restart_test",
                    "idempotency_key": f"restart-transition-{sequence:04d}",
                },
            )
            assert transitioned.status_code == 200

    async with app_client() as (client, app):
        socket = BrowserSocket()
        service = app.state.service  # type: ignore[attr-defined]
        service.browser_socket = socket
        service.browser_worker_connected = True
        await service.recover_browser_runs(uuid4())

        restored = await client.get("/v1/runs")
        assert restored.json()[0]["id"] == run_id
        assert restored.json()[0]["state"] == "filling"
        assert socket.messages[0]["action"] == "navigate"
        checkpoint = await client.get(f"/v1/runs/{run_id}/checkpoint")
        assert checkpoint.json()["state"] == "filling"
        assert checkpoint.json()["stepId"] == "automatic_browser_recovery"
