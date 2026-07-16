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

    inserted = 0
    skipped = 0

    for item in news_list:
        block = item.get("content", {}) or {}
        title = block.get("title") or ""
        content = block.get("summary") or ""
        source = (block.get("provider") or {}).get("displayName") or ""

        # A passage with no summary is not retrievable and the embeddings API
        # rejects empty input, so there is nothing to store.
        if not content.strip():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO public.news_chunks (source, title, content, chunk)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (source, title, content, content))
        inserted += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    return inserted, skipped


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
