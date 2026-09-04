"""Create versioned normalized job postings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_job_postings"
down_revision: str | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_postings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(36), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("resolved_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("description_hash", sa.String(64), nullable=False),
        sa.Column("requirements_json", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("platform_confidence", sa.Float(), nullable=False),
        sa.Column("platform_signals_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_url", "description_hash", name="uq_job_posting_content"),
    )
    op.create_index("ix_job_postings_canonical_url", "job_postings", ["canonical_url"])
    op.create_index("ix_job_postings_description_hash", "job_postings", ["description_hash"])
    op.create_index("ix_job_postings_platform", "job_postings", ["platform"])
    op.create_index("ix_job_postings_status", "job_postings", ["status"])


def downgrade() -> None:
    op.drop_table("job_postings")
