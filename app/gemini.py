import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

EMBED_MODEL = "gemini-embedding-2"

# The -latest alias rather than a pinned version, deliberately: gemini-2.0-flash
# was shut down and 2.5-flash is closed to new keys, so pinning is what breaks.
# The full flash models (3.5-flash, flash-latest) return 503 on the free tier;
# flash-lite is what a free key can actually reach.
CHAT_MODEL = "gemini-flash-lite-latest"

# gemini-embedding-2 is matryoshka, so 768 is a truncation of the full 3072
# rather than a weaker model, and it auto-normalises truncated dimensions.
# Smaller vectors also stay under pgvector's 2000-dimension ceiling, which
# leaves the door open to an HNSW index if the corpus ever outgrows a scan.
DIMENSIONS = 768

_client = None


def get_client():
    """Build the client lazily.

    Constructing at import time would take the whole app down on a missing key,
    including the routes that never call Gemini.
    """
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def _embed(text, task_type):
    response = get_client().models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=DIMENSIONS,
        ),
    )
    return response.embeddings[0].values


def embed_document(text):
    """Embed a passage for storage."""
    return _embed(text, "RETRIEVAL_DOCUMENT")


def embed_query(text):
    """Embed a question for searching.

    Deliberately a different task_type to embed_document: the model places
    questions and the passages that answer them in the same region, which only
    works if each side is embedded as what it actually is.
    """
    return _embed(text, "RETRIEVAL_QUERY")


def generate(prompt):
    response = get_client().models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
    )
    return response.text
