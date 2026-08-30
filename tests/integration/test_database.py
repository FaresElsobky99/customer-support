import pytest

from backend.app.database.connection import get_db_connection


pytestmark = pytest.mark.integration


def test_postgresql_connection():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()

    assert result is not None
    assert "PostgreSQL" in result[0]
