from pathlib import Path

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.gemini import CHAT_MODEL, DIMENSIONS, EMBED_MODEL
from app.search import ask_llm, build_context, search_similar_news

app = FastAPI(title="FinanceRAG API")

INDEX_HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX_HTML)


@app.get("/api/health")
def health():
    # The page reads its colophon from here rather than hardcoding model names,
    # which drift the moment a model is swapped.
    return {
        "status": "ok",
        "service": "FinanceRAG API",
        "embed_model": EMBED_MODEL,
        "chat_model": CHAT_MODEL,
        "dimensions": DIMENSIONS,
    }


class QueryRequest(BaseModel):
    question: str


def snippet(text, limit=200):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


@app.post("/ask")
def ask_question(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        results = search_similar_news(question)
    except psycopg2.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not reach the news database: {exc}"
        )
    except Exception as exc:
        # Retrieval also embeds the query, so this covers the embedding call too.
        raise HTTPException(
            status_code=502,
            detail=f"Retrieval failed: {type(exc).__name__}: {exc}"
        )

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No news passages matched this question. Has the corpus been ingested?"
        )

    try:
        answer = ask_llm(question, build_context(results))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"The language model did not respond: {type(exc).__name__}: {exc}"
        )

    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "title": title,
                "content": snippet(content),
                "published_at": published_at.isoformat() if published_at else None,
                "url": url,
            }
            for title, content, published_at, url in results
        ]
    }
