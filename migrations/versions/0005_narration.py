"""Keep narration and pending voice samples separate from scene and source music."""

from alembic import op
import sqlalchemy as sa

revision = "0005_narration"
down_revision = "0004_scene_preview"


def upgrade():
    for name in ("narration", "voice_preview"):
        op.add_column("days", sa.Column(name, sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade():
    op.drop_column("days", "voice_preview")
    op.drop_column("days", "narration")
