from openai import OpenAI
import os
from dotenv import load_dotenv

from app.db import get_connection
from app.vectors import to_vector

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding


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

    for row_id, chunk in rows:
        emb = generate_embedding(chunk)

        cur.execute("""
            UPDATE public.news_chunks
            SET embedding = %s::vector
            WHERE id = %s;
        """, (to_vector(emb), row_id))

        print(f"Embedding stored for row id: {row_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ All embeddings generated and saved!")


if __name__ == "__main__":
    store_embeddings()
