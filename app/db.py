import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def get_connection():
    """Connect to Postgres.

    DATABASE_URL wins when it is set — hosted providers hand you one string,
    and the Vercel/Neon integration injects it — with the DB_* parts kept as
    the local fallback.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def test_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("DB connected:", cur.fetchone())
    cur.close()
    conn.close()


if __name__ == "__main__":
    test_db()
