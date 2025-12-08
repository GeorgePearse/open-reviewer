# BAD: Using psycopg2 instead of psycopg3
# Expected issues: psycopg2, psycopg3/psycopg, sql injection
import psycopg2


def get_user(user_id: int):
    conn = psycopg2.connect("postgresql://localhost/db")
    cursor = conn.cursor()
    # Also has SQL injection vulnerability
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()
