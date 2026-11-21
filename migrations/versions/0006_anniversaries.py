"""Diary collection filters and annual reminders."""
from alembic import op
import sqlalchemy as sa

revision = "0006_anniversaries"
down_revision = "0005_narration"


def upgrade():
    for table, name in (("days", "favorite"), ("user_preferences", "auto_anniversary"), ("user_preferences", "show_title")):
        op.add_column(table, sa.Column(name, sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("days", sa.Column("mood_tags", sa.JSON()))
    op.create_table("anniversaries", sa.Column("day_id", sa.String(36), primary_key=True),
                    sa.Column("year", sa.Integer(), nullable=False), sa.Column("clock", sa.String(5), nullable=False))
    op.create_table("anniversary_deliveries", sa.Column("day_id", sa.String(36), primary_key=True),
                    sa.Column("year", sa.Integer(), primary_key=True), sa.Column("status", sa.String(16), nullable=False),
                    sa.Column("retry_at", sa.DateTime()))


def downgrade():
    op.drop_table("anniversary_deliveries")
    op.drop_table("anniversaries")
    for table, name in (("days", "favorite"), ("days", "mood_tags"), ("user_preferences", "auto_anniversary"), ("user_preferences", "show_title")):
        op.drop_column(table, name)
