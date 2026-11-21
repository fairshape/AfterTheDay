"""Allow a Telegram user to choose their own calendar timezone."""
from alembic import op
import sqlalchemy as sa

revision = "0002_timezone"
down_revision = "0001_days"


def upgrade():
    op.create_table("user_preferences",
                    sa.Column("owner_id", sa.BigInteger(), primary_key=True),
                    sa.Column("timezone", sa.String(80), nullable=False))


def downgrade():
    op.drop_table("user_preferences")
