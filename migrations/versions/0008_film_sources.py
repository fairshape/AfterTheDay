"""Protect the source days of a saved edit."""

from alembic import op
import sqlalchemy as sa

revision = "0008_film_sources"
down_revision = "0007_life_films"


def upgrade():
    table = op.create_table(
        "film_sources",
        sa.Column(
            "film_id",
            sa.String(36),
            sa.ForeignKey("life_films.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "day_id", sa.String(36), sa.ForeignKey("days.id", ondelete="RESTRICT"), primary_key=True
        ),
    )
    op.create_index("ix_film_sources_day_id", "film_sources", ["day_id"])
    db = op.get_bind()
    films = sa.table("life_films", sa.column("id"), sa.column("film", sa.JSON))
    for film_id, film in db.execute(sa.select(films.c.id, films.c.film)):
        ids = {shot["day"] for shot in film["shots"]}
        db.execute(table.insert(), [{"film_id": film_id, "day_id": day_id} for day_id in ids])


def downgrade():
    op.drop_table("film_sources")
