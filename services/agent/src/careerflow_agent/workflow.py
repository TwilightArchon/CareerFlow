from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from opentelemetry import metrics, trace
from sqlalchemy import func, select

from .contracts import WorkflowEvent, WorkflowState
from .database import Database, WorkflowEventRecord

TRACER = trace.get_tracer("careerflow.workflow")
METER = metrics.get_meter("careerflow.workflow")
TRANSITIONS = METER.create_counter("workflow_transitions_total")

ALLOWED_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.CREATED: frozenset({WorkflowState.INGESTING_JOB, WorkflowState.CANCELLED}),
    WorkflowState.INGESTING_JOB: frozenset(
        {
            WorkflowState.PREPARING_MATERIALS,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.PREPARING_MATERIALS: frozenset(
        {
            WorkflowState.OPENING_APPLICATION,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.OPENING_APPLICATION: frozenset(
        {
            WorkflowState.AUTHENTICATING,
            WorkflowState.FILLING,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.AUTHENTICATING: frozenset(
        {
            WorkflowState.REGISTERING,
            WorkflowState.FILLING,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.REGISTERING: frozenset(
        {
            WorkflowState.VERIFYING_EMAIL,
            WorkflowState.FILLING,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.VERIFYING_EMAIL: frozenset(
        {
            WorkflowState.FILLING,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.FILLING: frozenset(
        {
            WorkflowState.VALIDATING,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.AWAITING_HUMAN: frozenset(
        {
            WorkflowState.FILLING,
            WorkflowState.VALIDATING,
            WorkflowState.READY_TO_SUBMIT,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.VALIDATING: frozenset(
        {
            WorkflowState.FILLING,
            WorkflowState.READY_TO_SUBMIT,
            WorkflowState.AWAITING_HUMAN,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.READY_TO_SUBMIT: frozenset(
        {WorkflowState.SUBMITTING, WorkflowState.AWAITING_HUMAN, WorkflowState.CANCELLED}
    ),
    WorkflowState.SUBMITTING: frozenset(
        {WorkflowState.SUBMITTED, WorkflowState.OUTCOME_UNCERTAIN, WorkflowState.FAILED}
    ),
    WorkflowState.SUBMITTED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
    WorkflowState.OUTCOME_UNCERTAIN: frozenset(),
}


class InvalidTransitionError(ValueError):
    pass


class RunNotFoundError(LookupError):
    pass


class WorkflowService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def transition(
        self,
        *,
        run_id: UUID,
        to_state: WorkflowState,
        reason_code: str,
        idempotency_key: str,
        safe_details: dict[str, str | int | float | bool | None] | None = None,
    ) -> WorkflowEvent:
        with TRACER.start_as_current_span("workflow.step") as span:
            span.set_attribute("careerflow.run_id", str(run_id))
            span.set_attribute("careerflow.workflow.to_state", to_state)
            async with self.database.sessions() as session, session.begin():
                existing = await session.scalar(
                    select(WorkflowEventRecord).where(
                        WorkflowEventRecord.run_id == str(run_id),
                        WorkflowEventRecord.idempotency_key == idempotency_key,
                    )
                )
                if existing:
                    return self._to_contract(existing)

                run = await self.database.get_run_record(session, run_id)
                if run is None:
                    raise RunNotFoundError(str(run_id))

                from_state = WorkflowState(run.state)
                if to_state not in ALLOWED_TRANSITIONS[from_state]:
                    raise InvalidTransitionError(
                        f"Cannot transition from {from_state} to {to_state}"
                    )

                if to_state is WorkflowState.SUBMITTING and not run.auto_submit_authorized:
                    raise InvalidTransitionError("Submission requires per-run authorization")

                sequence = (
                    await session.scalar(
                        select(func.coalesce(func.max(WorkflowEventRecord.sequence), 0)).where(
                            WorkflowEventRecord.run_id == str(run_id)
                        )
                    )
                    or 0
                ) + 1
                now = datetime.now(UTC)
                event = WorkflowEventRecord(
                    id=str(uuid4()),
                    run_id=str(run_id),
                    sequence=sequence,
                    event_type="state_transition",
                    from_state=from_state,
                    to_state=to_state,
                    reason_code=reason_code,
                    safe_details_json=json.dumps(safe_details or {}, separators=(",", ":")),
                    idempotency_key=idempotency_key,
                    occurred_at=now,
                )
                run.state = to_state
                run.updated_at = now
                session.add(event)

            TRANSITIONS.add(1, {"from_state": from_state, "to_state": to_state})
            return self._to_contract(event)

    @staticmethod
    def _to_contract(record: WorkflowEventRecord) -> WorkflowEvent:
        return WorkflowEvent(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            sequence=record.sequence,
            event_type=record.event_type,
            from_state=WorkflowState(record.from_state) if record.from_state else None,
            to_state=WorkflowState(record.to_state),
            reason_code=record.reason_code,
            safe_details=json.loads(record.safe_details_json),
            occurred_at=record.occurred_at,
        )
