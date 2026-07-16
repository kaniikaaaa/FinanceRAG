"""Bring public.news_chunks up to the schema the search code expects.

Safe to run more than once. Run this before ingest.py and embed.py.
"""
import psycopg2

from app.db import get_connection
from app.gemini import DIMENSIONS


def reconcile_dimensions(cur):
    """Re-type the column when it was built for a different embedding model.

    Vector width is fixed per model, so switching models makes every stored
    vector meaningless. Re-typing is only safe while the column is empty.
    """
    cur.execute("""
        SELECT format_type(atttypid, atttypmod)
        FROM pg_attribute
        WHERE attrelid = 'public.news_chunks'::regclass
          AND attname = 'embedding'
          AND NOT attisdropped;
    """)
    current = cur.fetchone()[0]
    want = f"vector({DIMENSIONS})"

    if current == want:
        print(f"embedding column is {want}")
        return

    cur.execute("SELECT count(embedding) FROM public.news_chunks;")
    embedded = cur.fetchone()[0]
    if embedded:
        print(
            f"WARNING: column is {current} but the model produces {want}, and "
            f"{embedded} rows are already embedded. Clear them, then re-run."
        )
        return

    cur.execute(f"ALTER TABLE public.news_chunks ALTER COLUMN embedding TYPE {want};")
    print(f"embedding column re-typed {current} -> {want}")


def ensure_unique_index(cur):
    """What makes ingest.py's ON CONFLICT DO NOTHING work.

    md5() keeps the key inside btree's size limit, which a long passage would
    otherwise exceed.
    """
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

    reconcile_dimensions(cur)
    ensure_unique_index(cur)

    cur.execute("SELECT count(*), count(embedding) FROM public.news_chunks;")
    total, embedded = cur.fetchone()
    print(f"{total} rows, {embedded} embedded, {total - embedded} awaiting embed.py")

    cur.close()
    conn.close()


if __name__ == "__main__":
    migrate()
