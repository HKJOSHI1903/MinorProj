"""Find the knowledge-base passages closest in meaning to a question."""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from .ingest import INDEX_DIR, embed, get_embedder

# Passages scoring below this are too loosely related to be worth showing.
# (Scores are cosine similarities between 0 and 1; tune on your own documents.)
MIN_SCORE = 0.35


class IndexNotBuilt(FileNotFoundError):
    pass


@lru_cache(maxsize=1)
def _load():
    """Return (index, chunks, embedder). Cached, because loading the embedder takes a few seconds."""
    index_path = INDEX_DIR / "index.faiss"
    chunks_path = INDEX_DIR / "chunks.json"
    if not index_path.exists() or not chunks_path.exists():
        raise IndexNotBuilt("The search index is missing. Run `python -m kisan.chatbot.ingest` first.")
    import faiss

    index = faiss.deserialize_index(np.frombuffer(index_path.read_bytes(), dtype="uint8"))
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    return index, chunks, get_embedder()


def document_count() -> int:
    _, chunks, _ = _load()
    return len({chunk["source"] for chunk in chunks})


def search(query: str, k: int = 4, min_score: float = MIN_SCORE) -> list[dict]:
    """The k passages most similar to the query, best first, each with its score."""
    index, chunks, embedder = _load()
    vector = embed(embedder, [query])
    scores, positions = index.search(vector, min(k, len(chunks)))
    return [
        {**chunks[position], "score": round(float(score), 3)}
        for score, position in zip(scores[0], positions[0])
        if position >= 0 and score >= min_score
    ]
