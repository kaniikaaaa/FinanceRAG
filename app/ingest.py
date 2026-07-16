import yfinance as yf

from app.db import get_connection


def fetch_news(ticker="AAPL"):
    stock = yf.Ticker(ticker)
    return stock.news


def save_news_to_db(news_list):
    conn = get_connection()
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.news_chunks (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            content TEXT,
            chunk TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if not news_list:
        print("⚠️ No news fetched from Yahoo Finance.")
        conn.close()
        return

    for item in news_list:
        # Correct structure according to Yahoo Finance response
        title = item.get("content", {}).get("title", "")
        content = item.get("content", {}).get("summary", "")
        source = item.get("content", {}).get("provider", {}).get("displayName", "")

        print("Inserting:", title[:60])

        cur.execute("""
            INSERT INTO public.news_chunks (source, title, content, chunk)
            VALUES (%s, %s, %s, %s)
        """, (source, title, content, content))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ News saved to database successfully!")


if __name__ == "__main__":
    # Try different tickers if needed: AAPL, TSLA, MSFT, NVDA
    news = fetch_news("AAPL")
    print("Fetched news:", news)
    print("Number of news items:", len(news))

    save_news_to_db(news)
