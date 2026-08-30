import psycopg

from backend.app.config import DATABASE_URL


def get_db_connection():
    """Return a new PostgreSQL connection."""

    return psycopg.connect(DATABASE_URL)
