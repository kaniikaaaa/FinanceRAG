# FinanceRAG

Ask questions about recent market news and get answers grounded in retrieved sources.

**Live:** https://finance-rag-one.vercel.app

Yahoo Finance headlines are ingested, embedded into pgvector, and searched by semantic
similarity. Every answer is composed only from the passages retrieved for that question,
and those passages are printed underneath it so the answer can be checked.

## Stack

FastAPI · Neon Postgres · pgvector · Gemini (`gemini-embedding-2`, `gemini-flash-lite-latest`) · yfinance

Runs entirely on free tiers.

## What's interesting here

- **The model declines rather than reaching.** Ask it about Nvidia when the corpus has no
  Nvidia coverage and it says so, then describes the AMD reporting it did find. The answer
  is built from the retrieved passages alone, never from what the model happens to remember.
- **Questions and passages are embedded differently.** Passages go in as
  `RETRIEVAL_DOCUMENT`, questions as `RETRIEVAL_QUERY`. They are not interchangeable —
  embedding both as the same thing measurably degrades retrieval.
- **Duplicate passages are impossible, not merely discouraged.** A unique index on
  `md5(chunk)` plus `ON CONFLICT DO NOTHING` means re-running ingest adds nothing. Without
  it a `k=3` search happily returned three copies of one story as if they were three sources.
- **768 dimensions, not 3072.** `gemini-embedding-2` is matryoshka, so the shorter vector is
  a truncation rather than a weaker model, and it arrives pre-normalised — which is why an
  L2 (`<->`) ordering ranks identically to cosine here.

## Run locally

```bash
git clone https://github.com/kaniikaaaa/FinanceRAG.git
cd FinanceRAG

python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env    # then fill in DATABASE_URL and GEMINI_API_KEY
```

Needs a Postgres with pgvector available — [Neon](https://neon.tech)'s free tier has it
built in. A free Gemini key comes from [AI Studio](https://aistudio.google.com/apikey).

```bash
python -m app.migrate               # extension, table, embedding column, unique index
python -m app.ingest AAPL TSLA      # pull news (defaults to AAPL TSLA MSFT NVDA)
python -m app.embed                 # embed anything not yet embedded
uvicorn app.main:app --reload
```

Run `migrate` first: it owns the schema. `ingest` and `embed` are both safe to re-run —
`ingest` skips passages it already has, `embed` skips rows it has already embedded.

## Keeping the corpus fresh

`.github/workflows/ingest.yml` runs `migrate → ingest → embed` against the same database
every six hours, and on demand from the Actions tab. It needs `DATABASE_URL` and
`GEMINI_API_KEY` as repository secrets.

This is the write path, and it deliberately does not live on Vercel: embedding is a batch
job measured in minutes, which is the one thing a serverless function's timeout cannot
accommodate. Vercel serves the read path, where a query is three network calls and no
state of its own.

## API

```
GET  /             the web UI (?q=... files a query directly)
GET  /api/health   status + the models actually in use
POST /ask          { "question": "what's driving chip stocks?" }
```

`/ask` returns:

```json
{
  "question": "...",
  "answer": "...",
  "sources": [{ "title": "...", "content": "..." }]
}
```

Failures come back as `{"detail": "..."}` with a status that says where it broke:
503 if the database is unreachable, 502 if retrieval or the model failed, 404 if nothing
in the corpus matched.

## Module layout

```
app/
├── main.py     FastAPI app — serves the UI and /ask
├── db.py       connection (prefers DATABASE_URL, falls back to DB_* parts)
├── migrate.py  owns the schema; run before ingest
├── ingest.py   yfinance news fetcher
├── embed.py    backfills embeddings
├── search.py   vector search + answer composition
├── gemini.py   Gemini client, model names, dimensions
└── vectors.py  renders an embedding as a pgvector literal
web/
└── index.html  the single-page UI
```

## Deploying

Vercel autodetects `app/main.py`, so no entrypoint config is needed — adding a
`pyproject.toml` actually breaks the build, because its presence switches Vercel from
`requirements.txt` to `uv`, which then demands a `[project]` table.

Set `DATABASE_URL` and `GEMINI_API_KEY` in Project Settings → Environment Variables, then
redeploy. Environment variables only reach a new build, not an existing deployment.

## License

MIT
