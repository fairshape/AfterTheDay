"""Store one unpublished scene candidate per memory."""
from alembic import op
import sqlalchemy as sa

revision = "0004_scene_preview"
down_revision = "0003_cover_style"


def upgrade():
    op.add_column("days", sa.Column("scene_preview", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade():
    op.drop_column("days", "scene_preview")
