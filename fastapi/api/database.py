import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Configuration from environment variables
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "workout")
DATABASE_USER = os.getenv("DATABASE_USER", "workoutadmin")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")

# For AWS: Parse secret from Secrets Manager JSON if provided
DATABASE_SECRET_JSON = os.getenv("DATABASE_SECRET_JSON")
if DATABASE_SECRET_JSON:
    secret = json.loads(DATABASE_SECRET_JSON)
    DATABASE_HOST = secret.get("host", DATABASE_HOST)
    DATABASE_PORT = str(secret.get("port", DATABASE_PORT))
    DATABASE_NAME = secret.get("dbname", DATABASE_NAME)
    DATABASE_USER = secret.get("username", DATABASE_USER)
    DATABASE_PASSWORD = secret.get("password", DATABASE_PASSWORD)


def get_connection():
    """Create and return a new database connection."""
    return psycopg2.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
    )


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor():
    """Context manager for database cursors with dict results."""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
        finally:
            cursor.close()


def init_db():
    """Initialize the database schema."""
    with get_cursor() as cursor:
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                cognito_sub VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                message VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
