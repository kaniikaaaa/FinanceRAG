import sys

import yfinance as yf

from app.db import get_connection

TICKERS = ["AAPL", "TSLA", "MSFT", "NVDA"]


def fetch_news(ticker):
    stock = yf.Ticker(ticker)
    return stock.news


def save_news_to_db(news_list):
    """Insert news passages. Run migrate.py first — it owns the schema.

    Repeat headlines are dropped by the unique index on md5(chunk), so running
    this twice over the same wire adds nothing the second time.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM public.news_chunks;")
    before = cur.fetchone()[0]
    skipped = 0

    for item in news_list:
        block = item.get("content", {}) or {}
        title = block.get("title") or ""
        content = block.get("summary") or ""
        source = (block.get("provider") or {}).get("displayName") or ""
        published_at = block.get("pubDate") or block.get("displayTime") or None
        url = (block.get("canonicalUrl") or {}).get("url") or None

        # A passage with no summary is not retrievable and the embeddings API
        # rejects empty input, so there is nothing to store.
        if not content.strip():
            skipped += 1
            continue

        # DO UPDATE rather than DO NOTHING so a passage stored before we kept
        # dates and links picks them up on the next run. COALESCE keeps what we
        # already have when the wire omits a field.
        cur.execute("""
            INSERT INTO public.news_chunks (source, title, content, chunk, url, published_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT ((md5(chunk))) DO UPDATE
            SET url          = COALESCE(EXCLUDED.url, public.news_chunks.url),
                published_at = COALESCE(EXCLUDED.published_at, public.news_chunks.published_at)
        """, (source, title, content, content, url, published_at))

    conn.commit()
    cur.execute("SELECT count(*) FROM public.news_chunks;")
    after = cur.fetchone()[0]

    cur.close()
    conn.close()
    return after - before, skipped


if __name__ == "__main__":
    tickers = [t.upper() for t in sys.argv[1:]] or TICKERS

    total_new = 0
    for ticker in tickers:
        news = fetch_news(ticker)
        if not news:
            print(f"WARNING: {ticker}: no news returned by Yahoo Finance")
            continue
        inserted, skipped = save_news_to_db(news)
        total_new += inserted
        print(f"{ticker}: {len(news)} fetched, {inserted} new, {skipped} without a summary")

    print(f"{total_new} new passages saved. Run embed.py next.")
