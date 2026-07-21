"""A small, dependency-free TF-IDF retrieval index over the menu/recipe docs.

The corpus is tiny (~17 short documents) and static, so a neural embedding
model would be overkill for this project's scope - classic TF-IDF + cosine
similarity is enough to route a question like "what's in the peri-peri
chicken?" to the right doc, and it needs no API key, network call, or extra
ML dependency. search() is the only thing callers depend on, so this could
be swapped for a real embedding model later without touching them.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "menu_docs"
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass
class IndexedDoc:
    path: Path
    text: str
    weights: dict[str, float]
    norm: float


@dataclass
class Index:
    docs: list[IndexedDoc]
    idf: dict[str, float]


def _build_index() -> Index:
    paths = sorted(DOCS_DIR.glob("*.md"))
    if not paths:
        raise FileNotFoundError(
            f"No docs in {DOCS_DIR}. Run `python -m app.retrieval.build_docs` first."
        )

    parsed = [(path, path.read_text(encoding="utf-8")) for path in paths]
    parsed = [(path, text, tokenize(text)) for path, text in parsed]

    doc_count = len(parsed)
    doc_freq: Counter = Counter()
    for _, _, tokens in parsed:
        doc_freq.update(set(tokens))
    # Smooth idf (as in scikit-learn's default): avoids zero/negative weights.
    idf = {term: math.log((1 + doc_count) / (1 + df)) + 1 for term, df in doc_freq.items()}

    docs = []
    for path, text, tokens in parsed:
        weights = {term: freq * idf[term] for term, freq in Counter(tokens).items()}
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
        docs.append(IndexedDoc(path=path, text=text, weights=weights, norm=norm))
    return Index(docs=docs, idf=idf)


@lru_cache(maxsize=1)
def _cached_index() -> Index:
    return _build_index()


def search(query: str, top_k: int = 3) -> list[tuple[str, float, str]]:
    """Returns up to top_k (filename, cosine_score, doc_text) tuples, best match
    first. A query that shares no vocabulary with any doc returns []."""
    index = _cached_index()

    query_terms = Counter(tokenize(query))
    query_weights = {
        term: freq * index.idf[term] for term, freq in query_terms.items() if term in index.idf
    }
    query_norm = math.sqrt(sum(w * w for w in query_weights.values())) or 1.0

    scored = []
    for doc in index.docs:
        dot = sum(query_weights.get(term, 0.0) * w for term, w in doc.weights.items())
        score = dot / (query_norm * doc.norm)
        if score > 0:
            scored.append((doc.path.name, score, doc.text))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


def retrieve_context(query: str, top_k: int = 2) -> str | None:
    """Formats the top matching docs into one string for the stage-2 prompt."""
    matches = search(query, top_k=top_k)
    if not matches:
        return None
    return "\n\n---\n\n".join(text for _, _, text in matches)


def reset_index_cache() -> None:
    """For tests/tools that rebuild menu_docs mid-process."""
    _cached_index.cache_clear()
