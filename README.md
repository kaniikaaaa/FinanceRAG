# FinanceRAG

Ask questions about recent market news and get cited answers. Ingests Yahoo Finance headlines on a schedule, embeds them into pgvector, and serves a retrieval-augmented endpoint that ranks on semantic similarity + recency.

## Stack

FastAPI · PostgreSQL · pgvector · OpenAI `text-embedding-3-large` · GPT-4o-mini · yfinance · SQLAlchemy

## What's interesting here

- **Recency-weighted retrieval.** Vector similarity alone surfaces stale analysis; retrieval score blends cosine distance with an exponential decay on publish time, so a question about "today's tech drop" retrieves today's news, not last month's.
- **Cited answers by construction.** Every response returns the top-K source chunks with title, publish time, and ticker. No citation means no answer; the model refuses rather than fabricating.
- **Sub-second hot path.** Embeddings are pre-computed on ingest and stored alongside the raw doc, so the query path is one pgvector `<->` op + one GPT-4o-mini call.

## Run locally

```bash
git clone https://github.com/kaniikaaaa/FinanceRAG.git
cd FinanceRAG

python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # add OPENAI_API_KEY, DATABASE_URL

# Assumes a local Postgres with the pgvector extension enabled:
# CREATE EXTENSION IF NOT EXISTS vector;
python -m app.db            # creates tables
python -m app.ingest        # pulls news + embeds
uvicorn app.main:app --reload
```

## API

```
POST /query
Body: { "question": "what's driving NVDA today?", "top_k": 5 }
Returns: { "answer": "...", "sources": [{ title, url, ticker, published_at }] }
```

## Module layout

```
app/
├── main.py     FastAPI entry
├── api.py      /query + /ingest routes
├── db.py       SQLAlchemy models + pgvector schema
├── embed.py    OpenAI embedding client
├── ingest.py   yfinance news fetcher
└── search.py   recency-weighted retrieval
```

## License

MIT
