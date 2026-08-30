from backend.app.database.connection import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT version();")
        result = cursor.fetchone()

        print(result)
