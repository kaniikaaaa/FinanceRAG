from datetime import date

from app.db import get_connection
from app.gemini import embed_query, generate
from app.vectors import to_vector

# Similarity alone surfaces whatever matches best regardless of age, which is
# wrong for a news corpus: a stale story that matches well should lose to a
# fresh one that matches nearly as well. Passages carry a distance penalty that
# grows with age — nothing at all when new, approaching RECENCY_WEIGHT when
# ancient, and ~63% of the way there at RECENCY_DECAY_DAYS old.
RECENCY_WEIGHT = 0.35
RECENCY_DECAY_DAYS = 7.0


def get_query_embedding(query):
    return embed_query(query)


def search_similar_news(query, k=3):
    query_embedding = get_query_embedding(query)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title,
               content,
               -- The same date the ranking below scores on. Passages stored
               -- before we captured pubDate fall back to when we fetched them,
               -- which is close enough: they came off a live wire.
               COALESCE(published_at, created_at AT TIME ZONE 'UTC') AS published_at,
               url
        FROM public.news_chunks
        WHERE embedding IS NOT NULL
        ORDER BY (embedding <-> %s::vector)
               + %s * (1 - exp(
                     -GREATEST(0, EXTRACT(EPOCH FROM (
                         now() - COALESCE(published_at, created_at AT TIME ZONE 'UTC')
                     )))
                     / (86400.0 * %s)
                 ))
        LIMIT %s;
    """, (to_vector(query_embedding), RECENCY_WEIGHT, RECENCY_DECAY_DAYS, k))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return results


def build_context(results):
    """Date every passage, so the model can tell current reporting from old."""
    context = ""
    for title, content, published_at, _url in results:
        when = published_at.strftime("%d %b %Y") if published_at else "date unknown"
        context += f"\nTitle: {title}\nPublished: {when}\n{content}\n"
    return context


def ask_llm(query, context):
    prompt = f"""
Use the following finance news to answer the question. Today is {date.today():%d %B %Y}.

Each passage is dated. Lead with the most recent reporting, and if the only
relevant passage is more than a few days old, say so rather than presenting it
as the current picture. Answer only from these passages.

Context:
{context}

Question:
{query}
"""

    return generate(prompt)


if __name__ == "__main__":
    query = input("Ask something about finance news: ")

    results = search_similar_news(query)
    answer = ask_llm(query, build_context(results))
    print("\nAnswer:\n", answer)
