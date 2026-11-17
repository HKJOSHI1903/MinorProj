"""Build the search index for the assistant from the files in knowledge_base/.

    python -m kisan.chatbot.ingest

RAG (retrieval-augmented generation) in three steps:
1. Chunk:  each document is split into passages, one per "## section".
2. Embed:  every passage is turned into a vector (384 numbers) by a multilingual
           sentence-embedding model. Passages with similar meaning get similar
           vectors, and a Hindi question lands near the English passage that answers it.
3. Store:  the vectors go into a FAISS index, which finds the nearest ones quickly.

Run this again whenever the documents change. The first run downloads the
embedding model (about 220 MB) into models/embeddings/.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "knowledge_base"
INDEX_DIR = ROOT / "models" / "kb"
EMBEDDING_CACHE = ROOT / "models" / "embeddings"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MAX_CHARS = 1200   # a longer section is split further, at paragraph ends
MIN_CHARS = 60     # shorter leftovers are not worth indexing


def split_long(text: str) -> list[str]:
    """Split text into pieces of at most MAX_CHARS, cutting at paragraph or sentence ends."""
    if len(text) <= MAX_CHARS:
        return [text]
    pieces, current = [], ""
    for part in re.split(r"(?<=[.!?।])\s+|\n{2,}", text):
        if current and len(current) + len(part) + 1 > MAX_CHARS:
            pieces.append(current.strip())
            current = part
        else:
            current = f"{current} {part}".strip()
    if current:
        pieces.append(current.strip())
    return pieces


def chunk_document(path: Path) -> list[dict]:
    """One chunk per '## section'. Each chunk remembers its document and section title."""
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem.replace("_", " ").title()

    chunks = []
    sections = re.split(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    # sections = [text before the first heading, heading 1, body 1, heading 2, body 2, ...]
    for heading, body in zip(sections[1::2], sections[2::2]):
        body = re.sub(r"\s+\n", "\n", body).strip()
        for piece in split_long(body):
            if len(piece) >= MIN_CHARS:
                chunks.append({"source": path.name, "title": title, "section": heading.strip(), "text": piece})
    return chunks


def load_chunks(docs_dir: Path = DOCS_DIR) -> list[dict]:
    chunks = []
    for path in sorted(docs_dir.glob("*")):
        if path.suffix.lower() in {".md", ".txt"} and path.name.lower() != "readme.md":
            chunks.extend(chunk_document(path))
    return chunks


def get_embedder():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=str(EMBEDDING_CACHE))


def embed(embedder, texts: list[str]) -> np.ndarray:
    """Vectors scaled to length 1, so the inner product of two vectors is their cosine similarity."""
    vectors = np.array(list(embedder.embed(texts)), dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def passage_text(chunk: dict) -> str:
    """What gets embedded: the titles are included because they carry meaning too."""
    return f"{chunk['title']} - {chunk['section']}\n{chunk['text']}"


def build_index(docs_dir: Path = DOCS_DIR, index_dir: Path = INDEX_DIR) -> int:
    import faiss

    chunks = load_chunks(docs_dir)
    if not chunks:
        raise SystemExit(f"No documents found in {docs_dir}.")
    vectors = embed(get_embedder(), [passage_text(chunk) for chunk in chunks])

    index = faiss.IndexFlatIP(vectors.shape[1])  # exact search by inner product
    index.add(vectors)

    index_dir.mkdir(parents=True, exist_ok=True)
    # FAISS cannot open paths with non-English characters on Windows, so the bytes are written by Python.
    (index_dir / "index.faiss").write_bytes(faiss.serialize_index(index).tobytes())
    (index_dir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(chunks)


def main() -> None:
    count = build_index()
    documents = len({chunk["source"] for chunk in load_chunks()})
    print(f"Indexed {count} passages from {documents} documents into {INDEX_DIR}")


if __name__ == "__main__":
    main()
