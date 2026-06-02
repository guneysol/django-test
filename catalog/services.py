"""Third-party API integration: the Open Library book search API.

Open Library (https://openlibrary.org/dev/docs/api/search) is a free, no-key
public API. We use it to import real book metadata into the catalog. The
network call is isolated here so it can be mocked in tests and reused by both
the management command and any future view.
"""

import requests

OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"


class OpenLibraryError(Exception):
    """Raised when the Open Library API cannot be reached or returns junk."""


def search_books(query, limit=5, timeout=10):
    """Return a list of normalised book dicts for a search ``query``.

    Each dict has the keys: ``title``, ``author``, ``published_year`` and
    ``description``. Raises :class:`OpenLibraryError` on network/parse failure.
    """
    params = {"q": query, "limit": limit, "fields": "title,author_name,first_publish_year"}
    try:
        resp = requests.get(OPEN_LIBRARY_SEARCH, params=params, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise OpenLibraryError(f"Open Library request failed: {exc}") from exc

    results = []
    for doc in payload.get("docs", []):
        authors = doc.get("author_name") or ["Unknown"]
        results.append(
            {
                "title": doc.get("title", "").strip()[:200],
                "author": authors[0].strip()[:120],
                "published_year": doc.get("first_publish_year"),
                "description": f"Imported from Open Library (search: “{query}”).",
            }
        )
    return [r for r in results if r["title"]]
