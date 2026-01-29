from fastapi import FastAPI
from pydantic import BaseModel
from app.search import search_similar_news, ask_llm


app = FastAPI(title="FinanceRAG API")
@app.get("/")
def root():
    return {"message": "FinanceRAG API is running 🚀"}


class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
def ask_question(req: QueryRequest):
    results = search_similar_news(req.question)

    context = ""
    for title, content in results:
        context += f"\nTitle: {title}\n{content}\n"

    answer = ask_llm(req.question, context)

    return {
        "question": req.question,
        "answer": answer,
        "sources": [
            {"title": title, "content": content[:200]}
            for title, content in results
        ]
    }
