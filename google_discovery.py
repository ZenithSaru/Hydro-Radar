"""
Sprint 4 client: Google Programmable Search (Custom Search JSON API).

Requires two secrets:
  GOOGLE_API_KEY — from https://console.cloud.google.com/apis/credentials
  GOOGLE_CSE_ID  — a Programmable Search Engine ID configured to search the
                   entire web: https://programmablesearchengine.google.com/

Free tier is 100 queries/day; each call here uses 1 query.
"""
import os
import requests

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleSearchNotConfigured(Exception):
    pass


def search(query: str, num: int = 10):
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise GoogleSearchNotConfigured(
            "GOOGLE_API_KEY / GOOGLE_CSE_ID not set — see README for setup."
        )

    resp = requests.get(
        SEARCH_URL,
        params={"key": api_key, "cx": cse_id, "q": query, "num": min(num, 10)},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    return [
        {
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]
