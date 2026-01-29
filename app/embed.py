from openai import OpenAI
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def generate_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding


def store_embeddings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, chunk FROM public.news_chunks WHERE embedding IS NULL;")
    rows = cur.fetchall()

    for row_id, chunk in rows:
        emb = generate_embedding(chunk)

        cur.execute("""
            UPDATE public.news_chunks
            SET embedding = %s
            WHERE id = %s;
        """, (emb, row_id))

        print(f"Embedding stored for row id: {row_id}")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ All embeddings generated and saved!")


if __name__ == "__main__":
    store_embeddings()
