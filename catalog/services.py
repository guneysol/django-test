"""External integrations and the AI insight service.

* Open Library (https://openlibrary.org) — a free, no-key public API used to
  import real book metadata and cover art.
* AI review summariser — generates a natural-language summary of a book's
  reviews. The implementation here is a lightweight, offline NLP heuristic
  (sentiment from ratings + keyword frequency), but it lives behind a single
  function so it can be swapped for a real LLM call (Claude / OpenAI) without
  touching the views or templates — see ``generate_ai_summary``.

Keeping all of this in one module means the network/AI logic can be mocked in
tests and reused by both management commands and views.
"""

import re
from collections import Counter

import requests

OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"


class OpenLibraryError(Exception):
    """Raised when the Open Library API cannot be reached or returns junk."""


def search_books(query, limit=5, timeout=10):
    """Return a list of normalised book dicts for a search ``query``.

    Each dict has the keys: ``title``, ``author``, ``published_year`` and
    ``description``. Raises :class:`OpenLibraryError` on network/parse failure.
    """
    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,first_publish_year,cover_i",
    }
    try:
        resp = requests.get(OPEN_LIBRARY_SEARCH, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise OpenLibraryError(f"Open Library request failed: {exc}") from exc

    results = []
    for doc in payload.get("docs", []):
        authors = doc.get("author_name") or ["Unknown"]
        cover_id = doc.get("cover_i")
        cover_url = (
            f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
        )
        results.append(
            {
                "title": doc.get("title", "").strip()[:200],
                "author": authors[0].strip()[:120],
                "published_year": doc.get("first_publish_year"),
                "cover_url": cover_url,
                "description": f"Imported from Open Library (search: “{query}”).",
            }
        )
    return [r for r in results if r["title"]]


# --- AI insight service ------------------------------------------------------

# Common English words to ignore when surfacing review "themes".
_STOPWORDS = {
    "this", "that", "with", "from", "have", "they", "their", "what", "when",
    "which", "would", "could", "about", "there", "them", "then", "than",
    "book", "books", "read", "reading", "really", "very", "just", "much",
    "some", "more", "most", "into", "your", "yours", "been", "were", "also",
    "like", "liked", "didn", "doesn", "isn", "story", "author", "characters",
    "character", "page", "pages", "chapter", "good", "great", "well",
}


def _extract_themes(reviews, limit=3):
    """Return the most-mentioned meaningful words across review text."""
    text = " ".join(f"{r.headline} {r.body}" for r in reviews).lower()
    words = re.findall(r"[a-z]{4,}", text)
    freq = Counter(w for w in words if w not in _STOPWORDS)
    return [word for word, _ in freq.most_common(limit)]


def generate_ai_summary(book):
    """Produce a short, natural-language summary of a book's reviews.

    Current implementation is a transparent heuristic: it derives sentiment
    from the average rating and surfaces recurring keywords as "themes". To use
    a real model instead, replace the body of this function with a call to an
    LLM (e.g. the Anthropic or OpenAI SDK) — the view/template contract is just
    ``(book) -> str``.
    """
    reviews = list(book.reviews.all())
    count = len(reviews)
    if count == 0:
        return "There aren't any reviews yet, so there's nothing to summarise. Be the first to share your thoughts!"

    avg = sum(r.rating for r in reviews) / count
    if avg >= 4.3:
        mood, verdict = "overwhelmingly positive", "a strong recommendation for most readers"
    elif avg >= 3.5:
        mood, verdict = "largely positive", "well worth picking up"
    elif avg >= 2.5:
        mood, verdict = "mixed", "one to approach depending on your taste"
    else:
        mood, verdict = "largely critical", "a divisive read that left many wanting"

    themes = _extract_themes(reviews)
    reviewers = "reviewer" if count == 1 else "reviewers"

    summary = (
        f"Across {count} {reviewers}, reception is {mood}, "
        f"averaging {avg:.1f} out of 5 stars."
    )
    if themes:
        theme_text = ", ".join(themes[:-1]) + (
            f" and {themes[-1]}" if len(themes) > 1 else themes[0]
        )
        summary += f" Recurring themes in the discussion include {theme_text}."
    summary += f" Overall, it's {verdict}."
    return summary
