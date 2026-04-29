"""
Vector store layer — Chroma + OpenAI embeddings.

Encapsulates everything related to storing and retrieving incidents:
  - Embedding text via OpenAI text-embedding-3-small
  - Persisting embeddings to a local Chroma collection
  - Querying for top-k similar incidents

Day 20: this module is exercised by scripts/seed_corpus.py and a manual
test in __main__. Day 21: the /triage endpoint will call retrieve_similar().
"""

import os
from typing import Optional
from openai import OpenAI
import chromadb

# OpenAI client. Reads OPENAI_API_KEY from environment automatically.
_openai_client: Optional[OpenAI] = None

# Chroma persistent client. Stores embeddings on disk in ./chroma_db/.
# Survives process restarts. Gitignored.
_chroma_client: Optional[chromadb.PersistentClient] = None

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions, cheap, well-known
COLLECTION_NAME = "incidents"


def _get_openai() -> OpenAI:
    """Lazy init the OpenAI client. Done lazily so importing this module
    doesn't crash if the key isn't set (e.g., in CI without secrets)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()  # picks up OPENAI_API_KEY from env
    return _openai_client


def _get_chroma() -> chromadb.PersistentClient:
    """Lazy init the Chroma client, persisted to ./chroma_db/."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path="./chroma_db")
    return _chroma_client


def get_collection():
    """Get or create the incidents collection."""
    return _get_chroma().get_or_create_collection(name=COLLECTION_NAME)


def embed_text(text: str) -> list[float]:
    """Embed a single string using OpenAI. Returns a 1536-dim vector."""
    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one API call. Cheaper than N single calls."""
    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def add_incidents(incidents: list[dict]) -> None:
    """
    Embed and store incidents in the Chroma collection.

    Each incident dict must have: id, title, description, resolution,
    severity, category, system. Embeds title + description + resolution
    (the resolution text is gold for similarity matching — past fixes are
    the strongest signal for triaging new incidents).
    """
    collection = get_collection()

    # Build the text to embed. This is the design decision: what goes in?
    # title + description + resolution. Documented in README later.
    texts = [
        f"{inc['title']}\n\n{inc['description']}\n\nResolution: {inc['resolution']}"
        for inc in incidents
    ]

    # Batch embed — one API call for all 30 incidents instead of 30 calls.
    embeddings = embed_texts(texts)

    # Chroma's metadata can't store nested dicts or lists, only flat scalars.
    # We pull out the structured fields we want returned at retrieval time.
    metadatas = [
        {
            "title": inc["title"],
            "system": inc["system"],
            "severity": inc["severity"],
            "category": inc["category"],
            "resolution": inc["resolution"],
        }
        for inc in incidents
    ]

    ids = [inc["id"] for inc in incidents]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,        # the embedded text — Chroma stores this for inspection
        metadatas=metadatas,    # the structured fields — returned on query
    )


def retrieve_similar(query: str, k: int = 3) -> list[dict]:
    """
    Find top-k incidents most similar to the query.

    Returns a list of dicts with the incident's id, title, system,
    severity, category, resolution, and the matched text. Sorted by
    similarity (closest first).
    """
    collection = get_collection()
    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    # Chroma returns parallel lists wrapped in an outer list (one entry per
    # query — we only sent one query, so [0] gets us the actual results).
    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return [
        {
            "id": id_,
            "title": meta["title"],
            "system": meta["system"],
            "severity": meta["severity"],
            "category": meta["category"],
            "resolution": meta["resolution"],
            "matched_text": doc,
            "distance": dist,  # lower = more similar (cosine distance)
        }
        for id_, doc, meta, dist in zip(ids, documents, metadatas, distances)
    ]