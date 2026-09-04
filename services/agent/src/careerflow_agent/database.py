from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .contracts import (
    ApplicationOutcome,
    ApplicationRun,
    ApplicationStatistics,
    Checkpoint,
    ConfirmationEvidence,
    CreateRunRequest,
    FieldExplanation,
    FieldMapping,
    JobIngestionStatus,
    JobPosting,
    JobRequirement,
    MappingDecision,
    OutcomeReasonCode,
    OutcomeType,
    Platform,
    PlatformDetection,
    Sensitivity,
    WorkflowEvent,
    WorkflowState,
)


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


class CheckpointRecord(Base):
    __tablename__ = "checkpoints"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_checkpoint_sequence"),
        UniqueConstraint("run_id", "idempotency_key", name="uq_checkpoint_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("application_runs.id"), index=True)
    step_id: Mapped[str] = mapped_column(String(128))
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class CandidateProfileRecord(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    encrypted_payload: Mapped[str] = mapped_column(Text)
    encryption_key_ref: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class JobPostingRecord(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("canonical_url", "description_hash", name="uq_job_posting_content"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, index=True)
    resolved_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    description_hash: Mapped[str] = mapped_column(String(64), index=True)
    requirements_json: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    platform_confidence: Mapped[float] = mapped_column(Float)
    platform_signals_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    warnings_json: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FieldExplanationRecord(Base):
    __tablename__ = "field_explanations"
    __table_args__ = (
        UniqueConstraint("run_id", "step_id", "control_id", name="uq_field_explanation_control"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("application_runs.id"), index=True)
    step_id: Mapped[str] = mapped_column(String(128))
    page_state_hash: Mapped[str] = mapped_column(String(128))
    control_id: Mapped[str] = mapped_column(String(200))
    canonical_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    sensitivity: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    filled: Mapped[bool] = mapped_column(Boolean)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ApplicationOutcomeRecord(Base):
    __tablename__ = "application_outcomes"
    __table_args__ = (
        UniqueConstraint("run_id", "revision", name="uq_application_outcome_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("application_runs.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    reason_code: Mapped[str] = mapped_column(String(96), index=True)
    confirmation_json: Mapped[str] = mapped_column(Text, default="[]")
    recorded_by: Mapped[str] = mapped_column(String(32))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


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
        async with self.sessions() as session:
            job = await session.get(JobPostingRecord, str(request.job_id))
        run = ApplicationRun(
            job_id=request.job_id,
            candidate_profile_id=request.candidate_profile_id,
            candidate_profile_version=request.candidate_profile_version,
            job_url=request.job_url,
            job_title=job.title if job else None,
            company=job.company if job else None,
            platform=Platform(job.platform) if job else None,
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
            runs: list[ApplicationRun] = []
            for row in result:
                job = await session.get(JobPostingRecord, row.job_id)
                outcome = await self._latest_outcome_record(session, UUID(row.id))
                runs.append(self._run_to_contract(row, job, outcome))
            return runs

    async def get_run(self, run_id: UUID) -> ApplicationRun | None:
        async with self.sessions() as session:
            record = await session.get(ApplicationRunRecord, str(run_id))
            if record is None:
                return None
            job = await session.get(JobPostingRecord, record.job_id)
            outcome = await self._latest_outcome_record(session, run_id)
            return self._run_to_contract(record, job, outcome)

    async def record_application_outcome(
        self,
        *,
        run_id: UUID,
        outcome: OutcomeType,
        reason_code: OutcomeReasonCode,
    ) -> ApplicationOutcome | None:
        async with self.sessions() as session, session.begin():
            run = await session.get(ApplicationRunRecord, str(run_id))
            if run is None:
                return None
            latest = await self._latest_outcome_record(session, run_id)
            if latest and latest.outcome == outcome and latest.reason_code == reason_code:
                return self._outcome_to_contract(latest)

            revision = latest.revision + 1 if latest else 1
            now = datetime.now(UTC)
            record_id = uuid4()
            confirmation: list[ConfirmationEvidence] = []
            if outcome is OutcomeType.SUBMITTED:
                fingerprint = sha256(
                    f"{run_id}:{revision}:{outcome}:{reason_code}".encode()
                ).hexdigest()
                confirmation.append(
                    ConfirmationEvidence(
                        kind="user_correction",
                        captured_at=now,
                        fingerprint=fingerprint,
                    )
                )
            record = ApplicationOutcomeRecord(
                id=str(record_id),
                run_id=str(run_id),
                revision=revision,
                supersedes_id=latest.id if latest else None,
                outcome=outcome,
                reason_code=reason_code,
                confirmation_json=json.dumps(
                    [item.model_dump(mode="json", by_alias=True) for item in confirmation],
                    separators=(",", ":"),
                ),
                recorded_by="user",
                recorded_at=now,
            )
            run.updated_at = now
            session.add(record)
            return self._outcome_to_contract(record)

    async def get_application_outcome(self, run_id: UUID) -> ApplicationOutcome | None:
        async with self.sessions() as session:
            record = await self._latest_outcome_record(session, run_id)
            return self._outcome_to_contract(record) if record else None

    async def list_application_outcomes(self, run_id: UUID) -> list[ApplicationOutcome]:
        async with self.sessions() as session:
            records = await session.scalars(
                select(ApplicationOutcomeRecord)
                .where(ApplicationOutcomeRecord.run_id == str(run_id))
                .order_by(ApplicationOutcomeRecord.revision)
            )
            return [self._outcome_to_contract(record) for record in records]

    async def application_statistics(self) -> ApplicationStatistics:
        async with self.sessions() as session:
            total_runs = int(
                await session.scalar(select(func.count()).select_from(ApplicationRunRecord)) or 0
            )
            records = list(
                await session.scalars(
                    select(ApplicationOutcomeRecord).order_by(
                        ApplicationOutcomeRecord.run_id,
                        ApplicationOutcomeRecord.revision.desc(),
                    )
                )
            )
        latest_by_run: dict[str, ApplicationOutcomeRecord] = {}
        for record in records:
            latest_by_run.setdefault(record.run_id, record)
        counts = {outcome: 0 for outcome in OutcomeType}
        for record in latest_by_run.values():
            counts[OutcomeType(record.outcome)] += 1
        resolved_runs = len(latest_by_run)
        submitted = counts[OutcomeType.SUBMITTED]
        return ApplicationStatistics(
            total_runs=total_runs,
            resolved_runs=resolved_runs,
            pending_runs=max(total_runs - resolved_runs, 0),
            submitted=submitted,
            failed=counts[OutcomeType.FAILED],
            cancelled=counts[OutcomeType.CANCELLED],
            abandoned=counts[OutcomeType.ABANDONED],
            outcome_uncertain=counts[OutcomeType.OUTCOME_UNCERTAIN],
            resolution_rate=resolved_runs / total_runs if total_runs else 0,
            submitted_rate=submitted / total_runs if total_runs else 0,
        )

    async def save_field_explanations(
        self,
        *,
        run_id: UUID,
        step_id: str,
        page_state_hash: str,
        mappings: list[FieldMapping],
        filled_control_ids: set[str],
    ) -> list[FieldExplanation]:
        now = datetime.now(UTC)
        async with self.sessions() as session, session.begin():
            for mapping in mappings:
                existing = await session.scalar(
                    select(FieldExplanationRecord).where(
                        FieldExplanationRecord.run_id == str(run_id),
                        FieldExplanationRecord.step_id == step_id,
                        FieldExplanationRecord.control_id == mapping.control_id,
                    )
                )
                if existing is None:
                    existing = FieldExplanationRecord(
                        id=str(uuid4()),
                        run_id=str(run_id),
                        step_id=step_id,
                        page_state_hash=page_state_hash,
                        control_id=mapping.control_id,
                        canonical_path=mapping.canonical_path,
                        source=mapping.source,
                        confidence=mapping.confidence,
                        sensitivity=mapping.sensitivity,
                        decision=mapping.decision,
                        rationale=mapping.rationale,
                        filled=mapping.control_id in filled_control_ids,
                        recorded_at=now,
                    )
                    session.add(existing)
                else:
                    existing.page_state_hash = page_state_hash
                    existing.canonical_path = mapping.canonical_path
                    existing.source = mapping.source
                    existing.confidence = mapping.confidence
                    existing.sensitivity = mapping.sensitivity
                    existing.decision = mapping.decision
                    existing.rationale = mapping.rationale
                    existing.filled = mapping.control_id in filled_control_ids
                    existing.recorded_at = now
        return await self.list_field_explanations(run_id)

    async def list_field_explanations(self, run_id: UUID) -> list[FieldExplanation]:
        async with self.sessions() as session:
            records = await session.scalars(
                select(FieldExplanationRecord)
                .where(FieldExplanationRecord.run_id == str(run_id))
                .order_by(FieldExplanationRecord.recorded_at, FieldExplanationRecord.control_id)
            )
            return [self._field_explanation_to_contract(record) for record in records]

    async def get_latest_profile_record(self) -> CandidateProfileRecord | None:
        async with self.sessions() as session:
            return await session.scalar(
                select(CandidateProfileRecord).order_by(CandidateProfileRecord.version.desc())
            )

    async def add_profile_record(self, record: CandidateProfileRecord) -> None:
        async with self.sessions() as session:
            session.add(record)
            await session.commit()

    async def save_job_posting(self, posting: JobPosting) -> JobPosting:
        async with self.sessions() as session, session.begin():
            existing = await session.scalar(
                select(JobPostingRecord).where(
                    JobPostingRecord.canonical_url == str(posting.canonical_url),
                    JobPostingRecord.description_hash == posting.description_hash,
                )
            )
            if existing:
                return self._job_to_contract(existing)

            latest = await session.scalar(
                select(JobPostingRecord)
                .where(JobPostingRecord.canonical_url == str(posting.canonical_url))
                .order_by(JobPostingRecord.version.desc())
            )
            posting.version = (latest.version + 1) if latest else 1
            posting.supersedes_id = UUID(latest.id) if latest else None
            record = JobPostingRecord(
                id=str(posting.id),
                version=posting.version,
                supersedes_id=str(posting.supersedes_id) if posting.supersedes_id else None,
                source_url=str(posting.source_url),
                canonical_url=str(posting.canonical_url),
                resolved_url=str(posting.resolved_url),
                title=posting.title,
                company=posting.company,
                location=posting.location,
                description=posting.description,
                description_hash=posting.description_hash,
                requirements_json=json.dumps(
                    [item.model_dump(mode="json", by_alias=True) for item in posting.requirements],
                    separators=(",", ":"),
                ),
                platform=posting.platform.platform,
                platform_confidence=posting.platform.confidence,
                platform_signals_json=json.dumps(posting.platform.signals, separators=(",", ":")),
                status=posting.status,
                warnings_json=json.dumps(posting.warnings, separators=(",", ":")),
                retrieved_at=posting.retrieved_at,
            )
            session.add(record)
            return posting

    async def get_job_posting(self, job_id: UUID) -> JobPosting | None:
        async with self.sessions() as session:
            record = await session.get(JobPostingRecord, str(job_id))
            return self._job_to_contract(record) if record else None

    async def get_run_record(
        self, session: AsyncSession, run_id: UUID
    ) -> ApplicationRunRecord | None:
        return await session.get(ApplicationRunRecord, str(run_id))

    async def get_event_by_idempotency(
        self, run_id: UUID, idempotency_key: str
    ) -> WorkflowEvent | None:
        async with self.sessions() as session:
            record = await session.scalar(
                select(WorkflowEventRecord).where(
                    WorkflowEventRecord.run_id == str(run_id),
                    WorkflowEventRecord.idempotency_key == idempotency_key,
                )
            )
            return self._event_to_contract(record) if record else None

    async def save_checkpoint(
        self,
        *,
        run_id: UUID,
        step_id: str,
        state: WorkflowState,
        idempotency_key: str,
    ) -> Checkpoint:
        async with self.sessions() as session, session.begin():
            existing = await session.scalar(
                select(CheckpointRecord).where(
                    CheckpointRecord.run_id == str(run_id),
                    CheckpointRecord.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return self._checkpoint_to_contract(existing)
            if await session.get(ApplicationRunRecord, str(run_id)) is None:
                raise LookupError(str(run_id))
            sequence = (
                await session.scalar(
                    select(func.coalesce(func.max(CheckpointRecord.sequence), 0)).where(
                        CheckpointRecord.run_id == str(run_id)
                    )
                )
                or 0
            ) + 1
            record = CheckpointRecord(
                id=str(uuid4()),
                run_id=str(run_id),
                step_id=step_id,
                sequence=sequence,
                state=state,
                idempotency_key=idempotency_key,
                created_at=datetime.now(UTC),
            )
            session.add(record)
            return self._checkpoint_to_contract(record)

    async def latest_checkpoint(self, run_id: UUID) -> Checkpoint | None:
        async with self.sessions() as session:
            record = await session.scalar(
                select(CheckpointRecord)
                .where(CheckpointRecord.run_id == str(run_id))
                .order_by(CheckpointRecord.sequence.desc())
                .limit(1)
            )
            return self._checkpoint_to_contract(record) if record else None

    @staticmethod
    async def _latest_outcome_record(
        session: AsyncSession, run_id: UUID
    ) -> ApplicationOutcomeRecord | None:
        return await session.scalar(
            select(ApplicationOutcomeRecord)
            .where(ApplicationOutcomeRecord.run_id == str(run_id))
            .order_by(ApplicationOutcomeRecord.revision.desc())
            .limit(1)
        )

    async def list_events(self, run_id: UUID) -> list[WorkflowEvent]:
        async with self.sessions() as session:
            result = await session.scalars(
                select(WorkflowEventRecord)
                .where(WorkflowEventRecord.run_id == str(run_id))
                .order_by(WorkflowEventRecord.sequence)
            )
            return [self._event_to_contract(row) for row in result]

    @staticmethod
    def _run_to_contract(
        record: ApplicationRunRecord,
        job: JobPostingRecord | None = None,
        outcome: ApplicationOutcomeRecord | None = None,
    ) -> ApplicationRun:
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
            job_title=job.title if job else None,
            company=job.company if job else None,
            platform=Platform(job.platform) if job else None,
            state=WorkflowState(record.state),
            latest_outcome=Database._outcome_to_contract(outcome) if outcome else None,
            auto_submit_authorized=record.auto_submit_authorized,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _outcome_to_contract(record: ApplicationOutcomeRecord) -> ApplicationOutcome:
        recorded_at = (
            record.recorded_at
            if record.recorded_at.tzinfo is not None
            else record.recorded_at.replace(tzinfo=UTC)
        )
        return ApplicationOutcome(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            revision=record.revision,
            supersedes_id=UUID(record.supersedes_id) if record.supersedes_id else None,
            outcome=OutcomeType(record.outcome),
            reason_code=OutcomeReasonCode(record.reason_code),
            confirmation=[
                ConfirmationEvidence.model_validate(item)
                for item in json.loads(record.confirmation_json)
            ],
            recorded_by="user",
            recorded_at=recorded_at,
        )

    @staticmethod
    def _job_to_contract(record: JobPostingRecord) -> JobPosting:
        retrieved_at = (
            record.retrieved_at
            if record.retrieved_at.tzinfo is not None
            else record.retrieved_at.replace(tzinfo=UTC)
        )
        return JobPosting(
            id=UUID(record.id),
            version=record.version,
            supersedes_id=UUID(record.supersedes_id) if record.supersedes_id else None,
            source_url=AnyHttpUrl(record.source_url),
            canonical_url=AnyHttpUrl(record.canonical_url),
            resolved_url=AnyHttpUrl(record.resolved_url),
            title=record.title,
            company=record.company,
            location=record.location,
            description=record.description,
            description_hash=record.description_hash,
            requirements=[
                JobRequirement.model_validate(item) for item in json.loads(record.requirements_json)
            ],
            platform=PlatformDetection(
                platform=Platform(record.platform),
                confidence=record.platform_confidence,
                signals=json.loads(record.platform_signals_json),
            ),
            status=JobIngestionStatus(record.status),
            warnings=json.loads(record.warnings_json),
            retrieved_at=retrieved_at,
        )

    @staticmethod
    def _field_explanation_to_contract(record: FieldExplanationRecord) -> FieldExplanation:
        recorded_at = (
            record.recorded_at
            if record.recorded_at.tzinfo is not None
            else record.recorded_at.replace(tzinfo=UTC)
        )
        return FieldExplanation(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            step_id=record.step_id,
            page_state_hash=record.page_state_hash,
            control_id=record.control_id,
            canonical_path=record.canonical_path,
            source=cast(Literal["adapter", "deterministic", "model", "user"], record.source),
            confidence=record.confidence,
            sensitivity=Sensitivity(record.sensitivity),
            decision=MappingDecision(record.decision),
            rationale=record.rationale,
            filled=record.filled,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _checkpoint_to_contract(record: CheckpointRecord) -> Checkpoint:
        created_at = (
            record.created_at
            if record.created_at.tzinfo is not None
            else record.created_at.replace(tzinfo=UTC)
        )
        return Checkpoint(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            step_id=record.step_id,
            sequence=record.sequence,
            state=WorkflowState(record.state),
            idempotency_key=record.idempotency_key,
            created_at=created_at,
        )

    @staticmethod
    def _event_to_contract(record: WorkflowEventRecord) -> WorkflowEvent:
        occurred_at = (
            record.occurred_at
            if record.occurred_at.tzinfo is not None
            else record.occurred_at.replace(tzinfo=UTC)
        )
        return WorkflowEvent(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            sequence=record.sequence,
            event_type=record.event_type,
            from_state=WorkflowState(record.from_state) if record.from_state else None,
            to_state=WorkflowState(record.to_state),
            reason_code=record.reason_code,
            safe_details=json.loads(record.safe_details_json),
            occurred_at=occurred_at,
        )
