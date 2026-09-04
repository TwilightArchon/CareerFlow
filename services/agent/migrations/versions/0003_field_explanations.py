"""Create durable field-level explanations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_field_explanations"
down_revision: str | None = "0002_job_postings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "field_explanations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("application_runs.id"),
            nullable=False,
        ),
        sa.Column("step_id", sa.String(128), nullable=False),
        sa.Column("page_state_hash", sa.String(128), nullable=False),
        sa.Column("control_id", sa.String(200), nullable=False),
        sa.Column("canonical_path", sa.String(200), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sensitivity", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("filled", sa.Boolean(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "step_id", "control_id", name="uq_field_explanation_control"),
    )
    op.create_index("ix_field_explanations_run_id", "field_explanations", ["run_id"])
    op.create_index("ix_field_explanations_recorded_at", "field_explanations", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("field_explanations")
