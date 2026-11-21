"""Persist drafts, original materials and published scenes."""
from alembic import op
import sqlalchemy as sa

revision = "0001_days"
down_revision = None


def upgrade():
    op.create_table(
        "days",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("memory_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("saved_at", sa.DateTime()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(24), nullable=False),
        sa.Column("story", sa.Text(), nullable=False),
        sa.Column("photos", sa.JSON(), nullable=False),
        sa.Column("track", sa.JSON(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("scene", sa.JSON(), nullable=False),
        sa.Column("comparison", sa.JSON(), nullable=False),
    )
    op.create_index("ix_days_owner_draft", "days", ["owner_id"], unique=True,
                    sqlite_where=sa.text("saved_at IS NULL"))
    op.create_index("ix_days_archive", "days", ["owner_id", "memory_date", "saved_at"])


def downgrade():
    op.drop_table("days")
