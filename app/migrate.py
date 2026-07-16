"""Bring public.news_chunks up to the schema the search code expects.

Safe to run more than once. Run this before embed.py.
"""
import psycopg2

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

    # What makes ingest.py's ON CONFLICT DO NOTHING work. md5() keeps the key
    # within btree's size limit, which a long passage would otherwise exceed.
    try:
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS news_chunks_chunk_uniq "
            "ON public.news_chunks (md5(chunk));"
        )
        print("unique index on chunk ready")
    except psycopg2.errors.UniqueViolation:
        cur.execute(
            "SELECT count(*) - count(DISTINCT md5(chunk)) FROM public.news_chunks "
            "WHERE chunk IS NOT NULL;"
        )
        print(
            f"WARNING: {cur.fetchone()[0]} duplicate chunks present, so the unique "
            f"index was not created. Remove the duplicates and re-run."
        )

    cur.execute("SELECT count(*), count(embedding) FROM public.news_chunks;")
    total, embedded = cur.fetchone()
    print(f"{total} rows, {embedded} embedded, {total - embedded} awaiting embed.py")

    cur.close()
    conn.close()


if __name__ == "__main__":
    migrate()
