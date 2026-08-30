from backend.app.database.connection import get_db_connection


def log_action(customer_id: int, role: str, tool_name: str) -> None:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_logs (customer_id, role, tool_name)
                VALUES (%s, %s, %s)
                """,
                (customer_id, role, tool_name),
            )
