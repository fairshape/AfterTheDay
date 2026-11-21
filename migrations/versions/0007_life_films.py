"""Saved private edits across multiple memories."""

import sqlalchemy as sa
from alembic import op

revision = "0007_life_films"
down_revision = "0006_anniversaries"


def upgrade():
    op.create_table(
        "life_films",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("film", sa.JSON(), nullable=False),
    )
    op.create_index("ix_life_films_owner_id", "life_films", ["owner_id"])


def downgrade():
    op.drop_table("life_films")
