from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker

from config.settings import ROOT


def open_database(directory: Path, migrate: bool):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(directory / "diary.sqlite3")))

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _record):
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")

    if migrate:
        config = Config(ROOT / "alembic.ini")
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    return sessionmaker(engine, expire_on_commit=False)
