from app.db import get_connection
from app.gemini import embed_document
from app.vectors import to_vector


def generate_embedding(text):
    return embed_document(text)


def store_embeddings():
    conn = get_connection()
    cur = conn.cursor()

    # Blank chunks are skipped: the embeddings API rejects empty input, and a
    # blank passage is not worth retrieving anyway.
    cur.execute("""
        SELECT id, chunk
        FROM public.news_chunks
        WHERE embedding IS NULL
          AND chunk IS NOT NULL
          AND btrim(chunk) <> '';
    """)
    rows = cur.fetchall()

    if not rows:
        print("Nothing to embed.")
        cur.close()
        conn.close()
        return

    print(f"Embedding {len(rows)} passages...")

    for row_id, chunk in rows:
        emb = generate_embedding(chunk)

        cur.execute("""
            UPDATE public.news_chunks
            SET embedding = %s::vector
            WHERE id = %s;
        """, (to_vector(emb), row_id))

        # Commit per row so a rate limit partway through does not throw away
        # the work already done — a rerun picks up where this stopped.
        conn.commit()
        print(f"Embedding stored for row id: {row_id}")

    cur.execute("SELECT count(*), count(embedding) FROM public.news_chunks;")
    total, embedded = cur.fetchone()

    cur.close()
    conn.close()
    print(f"All embeddings generated and saved. {embedded}/{total} rows embedded.")


if __name__ == "__main__":
    store_embeddings()
