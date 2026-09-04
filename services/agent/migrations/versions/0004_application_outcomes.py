"""Create append-only application outcome records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_application_outcomes"
down_revision: str | None = "0003_field_explanations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_outcomes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("application_runs.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(36), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("reason_code", sa.String(96), nullable=False),
        sa.Column("confirmation_json", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "revision", name="uq_application_outcome_revision"),
    )
    op.create_index("ix_application_outcomes_run_id", "application_outcomes", ["run_id"])
    op.create_index("ix_application_outcomes_outcome", "application_outcomes", ["outcome"])
    op.create_index("ix_application_outcomes_reason_code", "application_outcomes", ["reason_code"])
    op.create_index("ix_application_outcomes_recorded_at", "application_outcomes", ["recorded_at"])


def downgrade() -> None:
    op.drop_table("application_outcomes")
