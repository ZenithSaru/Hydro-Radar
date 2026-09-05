"""
Sprint 6 helper: rough recent-publication count via the Semantic Scholar
Academic Graph API (free, no key required for light use).

This is a heuristic, not identity-verified: author name search can collide
with other researchers sharing the same name. Treat publication_count as a
rough secondary signal, not ground truth — the award-based signal (a PI just
received NSF money) is the reliable part.
"""
import datetime
import requests

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/author/search"


def recent_publication_count(pi_name: str, years_back: int = 2):
    """Best-effort count of papers published by the top name-match author in
    the last `years_back` years. Returns None if the lookup fails or no
    match is found — callers should treat that as 'unknown', not zero.
    """
    if not pi_name or pi_name.strip() == "Unknown":
        return None

    try:
        resp = requests.get(
            SEARCH_URL,
            params={"query": pi_name, "fields": "name,paperCount,papers.year", "limit": 1},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    authors = data.get("data", [])
    if not authors:
        return None

    papers = authors[0].get("papers", []) or []
    cutoff_year = datetime.datetime.utcnow().year - years_back
    return sum(1 for p in papers if (p.get("year") or 0) >= cutoff_year)
