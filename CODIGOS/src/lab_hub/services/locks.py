"""PostgreSQL locks held across the commits performed by report jobs."""
from contextlib import contextmanager
from sqlalchemy import text


@contextmanager
def report_lock(db, key):
    with db.get_bind().connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("SELECT pg_advisory_lock(hashtextextended(:key, 0))"), {"key": key})
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"), {"key": key})
