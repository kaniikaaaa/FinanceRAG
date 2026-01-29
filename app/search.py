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


def get_query_embedding(query):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    return response.data[0].embedding


def search_similar_news(query, k=3):
    query_embedding = get_query_embedding(query)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, content
        FROM public.news_chunks
        ORDER BY embedding <-> %s
        LIMIT %s;
    """, (query_embedding, k))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def ask_llm(query, context):
    prompt = f"""
Use the following finance news to answer the question.

Context:
{context}

Question:
{query}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    query = input("Ask something about finance news: ")

    results = search_similar_news(query)

    context = ""
    for title, content in results:
        context += f"\nTitle: {title}\n{content}\n"

    answer = ask_llm(query, context)
    print("\n🤖 Answer:\n", answer)
