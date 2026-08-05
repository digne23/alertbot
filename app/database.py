import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger("alertbot.database")

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# Columns added after the first release. SQLite cannot ALTER a column, but it
# can add one, which is all we need — this keeps an existing alerts.db working
# instead of forcing you to delete incident history.
_MIGRATIONS: dict[str, dict[str, str]] = {
    "incidents": {
        "source": "VARCHAR DEFAULT 'email'",
        "notify_count": "INTEGER DEFAULT 0",
        "last_notified_at": "DATETIME",
        "escalation_level": "INTEGER DEFAULT 0",
        "escalated_at": "DATETIME",
        "silenced": "BOOLEAN DEFAULT 0",
    },
}


def _run_migrations() -> None:
    # SQLite has no real migration story; these ALTERs keep an existing
    # alerts.db usable. On PostgreSQL, create_all() plus a proper migration
    # tool takes over, so skip them.
    if not _is_sqlite:
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, columns in _MIGRATIONS.items():
            if table not in existing_tables:
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name in present:
                    continue
                logger.info("Migrating %s: adding column %s", table, name)
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    from app import models  # noqa: F401  ensure every model is registered

    _run_migrations()
    Base.metadata.create_all(bind=engine)

    from app.services import settings_service, rule_engine
    settings_service.seed_defaults()
    rule_engine.seed_rules()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
