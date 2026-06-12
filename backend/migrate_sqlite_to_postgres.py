import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import Base, DATABASE_PATH, DATABASE_URL

load_dotenv()

TABLES = [
    models.Firm,
    models.EmailLog,
    models.EmailTemplate,
    models.NewsletterDraft,
]


def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def main():
    sqlite_path = Path(os.getenv("SQLITE_MIGRATION_PATH", DATABASE_PATH))
    target_url = os.getenv("POSTGRES_DATABASE_URL", DATABASE_URL)

    if not sqlite_path.exists():
        print(f"SQLite database not found: {sqlite_path}")
        return 1

    if not target_url.startswith("postgresql"):
        print("Set POSTGRES_DATABASE_URL or DATABASE_URL to a PostgreSQL connection string.")
        return 1

    source_engine = create_engine(f"sqlite:///{sqlite_path.as_posix()}", connect_args={"check_same_thread": False})
    target_engine = create_engine(target_url, pool_pre_ping=True)
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    Base.metadata.create_all(bind=target_engine)

    with SourceSession() as source, TargetSession() as target:
        copied = {}

        for model in TABLES:
            existing_count = target.query(model.id).count()
            if existing_count:
                print(f"Skipping {model.__tablename__}; target already has {existing_count} rows.")
                continue

            rows = source.query(model).order_by(model.id.asc()).all()
            for row in rows:
                target.merge(model(**row_dict(row)))

            copied[model.__tablename__] = len(rows)

        target.commit()

    print("Migration complete:", copied)
    return 0


if __name__ == "__main__":
    sys.exit(main())
