from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import AnyHttpUrl
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .contracts import ApplicationRun, CreateRunRequest, WorkflowEvent, WorkflowState


class Base(DeclarativeBase):
    pass


class ApplicationRunRecord(Base):
    __tablename__ = "application_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_profile_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_profile_version: Mapped[int] = mapped_column(Integer)
    job_url: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(32), index=True)
    auto_submit_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    events: Mapped[list[WorkflowEventRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="WorkflowEventRecord.sequence"
    )


class WorkflowEventRecord(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_workflow_event_sequence"),
        UniqueConstraint("run_id", "idempotency_key", name="uq_workflow_event_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("application_runs.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(96))
    safe_details_json: Mapped[str] = mapped_column(Text, default="{}")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run: Mapped[ApplicationRunRecord] = relationship(back_populates="events")


class CandidateProfileRecord(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    encrypted_payload: Mapped[str] = mapped_column(Text)
    encryption_key_ref: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(database_url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.ready = False

    async def initialize(self) -> None:
        database_path = self.engine.url.database
        if database_path:
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.ready = True

    async def close(self) -> None:
        self.ready = False
        await self.engine.dispose()

    async def create_run(self, request: CreateRunRequest) -> ApplicationRun:
        run = ApplicationRun(
            job_id=request.job_id,
            candidate_profile_id=request.candidate_profile_id,
            candidate_profile_version=request.candidate_profile_version,
            job_url=request.job_url,
            auto_submit_authorized=request.auto_submit_authorized,
        )
        now = datetime.now(UTC)
        record = ApplicationRunRecord(
            id=str(run.id),
            job_id=str(run.job_id),
            candidate_profile_id=str(run.candidate_profile_id),
            candidate_profile_version=run.candidate_profile_version,
            job_url=str(run.job_url),
            state=run.state,
            auto_submit_authorized=run.auto_submit_authorized,
            created_at=now,
            updated_at=now,
        )
        async with self.sessions() as session:
            session.add(record)
            await session.commit()
        return run

    async def list_runs(self, *, limit: int = 100) -> list[ApplicationRun]:
        async with self.sessions() as session:
            result = await session.scalars(
                select(ApplicationRunRecord)
                .order_by(ApplicationRunRecord.updated_at.desc())
                .limit(limit)
            )
            return [self._run_to_contract(row) for row in result]

    async def get_latest_profile_record(self) -> CandidateProfileRecord | None:
        async with self.sessions() as session:
            return await session.scalar(
                select(CandidateProfileRecord).order_by(CandidateProfileRecord.version.desc())
            )

    async def add_profile_record(self, record: CandidateProfileRecord) -> None:
        async with self.sessions() as session:
            session.add(record)
            await session.commit()

    async def get_run_record(
        self, session: AsyncSession, run_id: UUID
    ) -> ApplicationRunRecord | None:
        return await session.get(ApplicationRunRecord, str(run_id))

    async def list_events(self, run_id: UUID) -> list[WorkflowEvent]:
        async with self.sessions() as session:
            result = await session.scalars(
                select(WorkflowEventRecord)
                .where(WorkflowEventRecord.run_id == str(run_id))
                .order_by(WorkflowEventRecord.sequence)
            )
            return [
                WorkflowEvent(
                    id=UUID(row.id),
                    run_id=run_id,
                    sequence=row.sequence,
                    event_type=row.event_type,
                    from_state=WorkflowState(row.from_state) if row.from_state else None,
                    to_state=WorkflowState(row.to_state),
                    reason_code=row.reason_code,
                    safe_details={},
                    occurred_at=row.occurred_at,
                )
                for row in result
            ]

    @staticmethod
    def _run_to_contract(record: ApplicationRunRecord) -> ApplicationRun:
        created_at = (
            record.created_at
            if record.created_at.tzinfo is not None
            else record.created_at.replace(tzinfo=UTC)
        )
        updated_at = (
            record.updated_at
            if record.updated_at.tzinfo is not None
            else record.updated_at.replace(tzinfo=UTC)
        )
        return ApplicationRun(
            id=UUID(record.id),
            job_id=UUID(record.job_id),
            candidate_profile_id=UUID(record.candidate_profile_id),
            candidate_profile_version=record.candidate_profile_version,
            job_url=AnyHttpUrl(record.job_url),
            state=WorkflowState(record.state),
            auto_submit_authorized=record.auto_submit_authorized,
            created_at=created_at,
            updated_at=updated_at,
        )
