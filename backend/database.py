import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Integer, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_PATH = Path(__file__).resolve().parent / "firms.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip() or DEFAULT_DATABASE_URL
IS_SQLITE = DATABASE_URL.startswith("sqlite")
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")

engine_kwargs = {"pool_pre_ping": True}
if IS_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


MINIMUM_POSTGRES_SEQUENCE_TABLES = (
    "firms",
    "email_logs",
    "users",
    "audit_logs",
    "email_templates",
    "newsletter_drafts",
)


def quote_identifier(identifier: str):
    return '"' + identifier.replace('"', '""') + '"'


def get_integer_primary_key_tables():
    tables = {
        table.name
        for table in Base.metadata.sorted_tables
        if "id" in table.c
        and table.c.id.primary_key
        and isinstance(table.c.id.type, Integer)
    }

    tables.update(MINIMUM_POSTGRES_SEQUENCE_TABLES)
    return sorted(tables)


def repair_postgresql_id_sequences(bind=engine):
    if not IS_POSTGRESQL:
        return []

    inspector = inspect(bind)
    repaired_tables = []

    with bind.begin() as connection:
        for table_name in get_integer_primary_key_tables():
            if not inspector.has_table(table_name):
                continue

            sequence_name = connection.execute(
                text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                {"table_name": table_name},
            ).scalar()

            if not sequence_name:
                continue

            quoted_table = quote_identifier(table_name)
            connection.execute(
                text(
                    "SELECT setval("
                    "pg_get_serial_sequence(:table_name, 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {quoted_table}), 1), "
                    "true"
                    ")"
                ),
                {"table_name": table_name},
            )
            repaired_tables.append(table_name)

    return repaired_tables
