from backend.app.database.connection import get_db_connection


def find_login_by_email(email: str):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password, role
                FROM customers
                WHERE email = %s
                """,
                (email,),
            )
            return cursor.fetchone()


def find_by_id(customer_id: int):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, status
                FROM customers
                WHERE id = %s
                """,
                (customer_id,),
            )
            return cursor.fetchone()


def find_status_by_id(customer_id: int):
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM customers
                WHERE id = %s
                """,
                (customer_id,),
            )
            return cursor.fetchone()


def find_all():
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, status, role
                FROM customers
                ORDER BY id
                """
            )
            return cursor.fetchall()
