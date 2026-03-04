from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.domain.base import Base


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _column_exists(connection, table_name: str, column_name: str) -> bool:
    inspector = inspect(connection)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _apply_lightweight_schema_upgrades() -> None:
    # Dev-friendly schema upgrades for incremental model changes without Alembic.
    # This prevents runtime crashes when code expects new columns in existing DB.
    with engine.begin() as connection:
        dialect = connection.dialect.name

        if not _column_exists(connection, "users", "subgroup_id"):
            connection.execute(text("ALTER TABLE users ADD COLUMN subgroup_id INTEGER"))

        if not _column_exists(connection, "resources", "parent_group_id"):
            connection.execute(text("ALTER TABLE resources ADD COLUMN parent_group_id INTEGER"))

        if not _column_exists(connection, "resources", "stream_id"):
            connection.execute(text("ALTER TABLE resources ADD COLUMN stream_id INTEGER"))

        if not _column_exists(connection, "mark_types", "is_archived"):
            connection.execute(
                text("ALTER TABLE mark_types ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE")
            )

        if not _column_exists(connection, "day_patterns", "is_archived"):
            connection.execute(
                text("ALTER TABLE day_patterns ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE")
            )

        if not _column_exists(connection, "week_patterns", "is_archived"):
            connection.execute(
                text("ALTER TABLE week_patterns ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE")
            )

        if not _column_exists(connection, "week_patterns", "name"):
            connection.execute(text("ALTER TABLE week_patterns ADD COLUMN name VARCHAR(120)"))

        if not _column_exists(connection, "room_profiles", "home_department_id"):
            connection.execute(text("ALTER TABLE room_profiles ADD COLUMN home_department_id INTEGER"))

        if dialect == "postgresql":
            connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_subgroup_id_resources'
                        ) THEN
                            ALTER TABLE users
                            ADD CONSTRAINT fk_users_subgroup_id_resources
                            FOREIGN KEY (subgroup_id) REFERENCES resources(id) ON DELETE SET NULL;
                        END IF;
                    END
                    $$;
                    """
                )
            )
            connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_resources_stream_id_streams'
                        ) THEN
                            ALTER TABLE resources
                            ADD CONSTRAINT fk_resources_stream_id_streams
                            FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE SET NULL;
                        END IF;
                    END
                    $$;
                    """
                )
            )
            connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_room_profiles_home_department_id_departments'
                        ) THEN
                            ALTER TABLE room_profiles
                            ADD CONSTRAINT fk_room_profiles_home_department_id_departments
                            FOREIGN KEY (home_department_id) REFERENCES departments(id) ON DELETE SET NULL;
                        END IF;
                    END
                    $$;
                    """
                )
            )
            connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'fk_resources_parent_group_id_resources'
                        ) THEN
                            ALTER TABLE resources
                            ADD CONSTRAINT fk_resources_parent_group_id_resources
                            FOREIGN KEY (parent_group_id) REFERENCES resources(id) ON DELETE CASCADE;
                        END IF;
                    END
                    $$;
                    """
                )
            )


def init_db(reset_schema: bool = False) -> None:
    import app.domain.models  # noqa: F401

    if reset_schema:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_schema_upgrades()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
