from app.db import get_connection
from app.gemini import embed_query, generate
from app.vectors import to_vector


def get_query_embedding(query):
    return embed_query(query)


def search_similar_news(query, k=3):
    query_embedding = get_query_embedding(query)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, content
        FROM public.news_chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> %s::vector
        LIMIT %s;
    """, (to_vector(query_embedding), k))

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

    return generate(prompt)


if __name__ == "__main__":
    query = input("Ask something about finance news: ")

    results = search_similar_news(query)

    context = ""
    for title, content in results:
        context += f"\nTitle: {title}\n{content}\n"

    answer = ask_llm(query, context)
    print("\nAnswer:\n", answer)
