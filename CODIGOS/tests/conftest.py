"""Run every destructive fixture in a new, disposable PostgreSQL database."""
import os
from pathlib import Path
import uuid
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config
from lab_hub.config import get_settings

settings = get_settings()
original = make_url(settings.TEST_DATABASE_URL).set(host="127.0.0.1")
database_name = "qrlabhub_verify_" + uuid.uuid4().hex[:12]
admin_url = original.set(drivername="postgresql", database="postgres")
with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as conn:
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
os.environ["DATABASE_URL"] = original.set(database=database_name).render_as_string(hide_password=False)
os.environ["REPORT_OUTPUT_DIR"] = str(Path("storage/test-reports") / database_name)
os.environ["LOCAL_DESKTOP_ACCESS"] = "false"
os.environ["LOCAL_SMTP_ENABLED"] = "false"
os.environ["EMAIL_ENABLED"] = "false"
os.environ["ADMIN_API_KEY"] = "labhub-dev-admin-key-2026"
get_settings.cache_clear()
command.upgrade(Config("alembic.ini"), "head")
from lab_hub.db.session import SessionLocal, engine
from lab_hub.services.seeds import seed_catalogs
with SessionLocal() as db:
    seed_catalogs(db)


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name)))
