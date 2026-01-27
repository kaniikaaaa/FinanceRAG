import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

# Load env variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financerag")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "kanika29")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DB CONFIG:", DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

# OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Get embedding using large model
def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return response.data[0].embedding


def main():
    # Connect to Postgres
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    # Fetch rows where embedding is NULL
    cur.execute("""
        SELECT id, content
        FROM public.news_chunks
        WHERE embedding IS NULL
        ORDER BY id;
    """)
    rows = cur.fetchall()

    if not rows:
        print("⚠️ No rows found without embeddings.")
        return

    for row in rows:
        row_id, content = row

        print(f"Generating embedding for row id: {row_id}")

        try:
            embedding = get_embedding(content)

            cur.execute("""
                UPDATE public.news_chunks
                SET embedding = %s
                WHERE id = %s
            """, (embedding, row_id))

            conn.commit()
            print(f"Embedding stored for row id: {row_id}")

        except Exception as e:
            print(f"❌ Error for row id {row_id}: {e}")
            conn.rollback()

    cur.close()
    conn.close()
    print("✅ All embeddings generated and saved!")


if __name__ == "__main__":
    main()
