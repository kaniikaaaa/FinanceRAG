import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path
import yfinance as yf

# Load .env from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

print("DB CONFIG:", DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


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
