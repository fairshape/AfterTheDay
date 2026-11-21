from alembic import context
from sqlalchemy import URL, create_engine

from app.infrastructure.db.models import Base
from config.settings import Settings


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    migrate(connection)
else:
    directory = Settings().storage
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(directory / "diary.sqlite3")))
    with engine.begin() as connection:
        migrate(connection)
