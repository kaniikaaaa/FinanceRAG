import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "financerag")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "kanika29")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DB CONFIG:", DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

client = OpenAI(api_key=OPENAI_API_KEY)


def get_query_embedding(query: str):
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    )
    return response.data[0].embedding


def search_similar_news(query, top_k=5):
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    query_embedding = get_query_embedding(query)

    # pgvector similarity search
    cur.execute("""
        SELECT title, source, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM public.news_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """, (query_embedding, query_embedding, top_k))

    results = cur.fetchall()
    cur.close()
    conn.close()

    return results


def ask_gpt(question, context):
    prompt = f"""
You are a finance news assistant.
Use the following news articles to answer the question.

Context:
{context}

Question:
{question}

Answer in simple and clear language.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful financial news assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    query = input("Ask something about finance news: ")

    results = search_similar_news(query)

    print("\n🔍 Top similar news articles:\n")

    combined_context = ""
    for i, (title, source, content, similarity) in enumerate(results, 1):
        print(f"{i}. {title} | {source} | Similarity: {round(similarity, 3)}\n")
        combined_context += f"Title: {title}\nContent: {content}\n\n"

    print("🤖 GPT Answer:\n")
    answer = ask_gpt(query, combined_context)
    print(answer)

