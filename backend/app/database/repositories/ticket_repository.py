from backend.app.database.connection import get_db_connection


def create(customer_id: int, issue: str) -> int:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tickets (customer_id, issue, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (customer_id, issue, "open"),
            )
            row = cursor.fetchone()

    return row[0]


def find_by_customer_id(customer_id: int):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, customer_id, issue, status
                FROM tickets
                WHERE customer_id = %s
                ORDER BY id
                """,
                (customer_id,),
            )
            return cursor.fetchall()


def find_all():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, customer_id, issue, status
                FROM tickets
                ORDER BY id
                """
            )
            return cursor.fetchall()


def update_status(ticket_id: int, status: str):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tickets
                SET status = %s
                WHERE id = %s
                RETURNING id, customer_id, issue, status
                """,
                (status, ticket_id),
            )
            return cursor.fetchone()
