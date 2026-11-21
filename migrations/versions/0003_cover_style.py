"""Store optional per-memory cover overrides."""

from alembic import op
import sqlalchemy as sa

revision = "0003_cover_style"
down_revision = "0002_timezone"


def upgrade():
    op.add_column("days", sa.Column("cover_style", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade():
    op.drop_column("days", "cover_style")
