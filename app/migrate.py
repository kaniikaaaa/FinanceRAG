"""Bring public.news_chunks up to the schema the search code expects.

Safe to run more than once. Run this before embed.py.
"""
from app.db import get_connection

# text-embedding-3-large returns 3072 dimensions. pgvector will not build an
# ivfflat or hnsw index above 2000, so this column stays unindexed and queries
# scan exactly — fine at this corpus size, and exact rather than approximate.
DIMENSIONS = 3072


def migrate():
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    print("pgvector extension ready")

    # Creates the table on a fresh database...
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS public.news_chunks (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            content TEXT,
            chunk TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            embedding vector({DIMENSIONS})
        );
    """)
    print("news_chunks table ready")

    # ...and brings an older table, created before embeddings existed, up to date.
    cur.execute(
        f"ALTER TABLE public.news_chunks "
        f"ADD COLUMN IF NOT EXISTS embedding vector({DIMENSIONS});"
    )
    print(f"embedding vector({DIMENSIONS}) column ready")

    cur.execute("SELECT count(*), count(embedding) FROM public.news_chunks;")
    total, embedded = cur.fetchone()
    print(f"{total} rows, {embedded} embedded, {total - embedded} awaiting embed.py")

    cur.close()
    conn.close()


if __name__ == "__main__":
    migrate()
