# BAD: SQL injection vulnerabilities
# Expected issues: SQL injection, parameterized, f-string, format
import psycopg


def get_user_by_name(conn: psycopg.Connection, name: str):
    """Get user by name - VULNERABLE to SQL injection."""
    # BAD: String formatting in SQL query
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return conn.execute(query).fetchone()


def search_products(conn: psycopg.Connection, search_term: str):
    """Search products - VULNERABLE to SQL injection."""
    # BAD: Using .format() for SQL
    query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
    return conn.execute(query).fetchall()


def delete_user(conn: psycopg.Connection, user_id: str):
    """Delete user - VULNERABLE to SQL injection."""
    # BAD: String concatenation
    query = "DELETE FROM users WHERE id = " + user_id
    conn.execute(query)
