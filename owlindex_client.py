"""
Sprint 2 client: scrapes Owlindex hashtag feeds for opportunity postings.

Owlindex doesn't offer a public API, so this parses the rendered hashtag
filter pages (e.g. https://www.owlindex.com/hashtags/filters?hashtag=Earth).
Each post links to a single_post_view page; where available we also pull the
schema.org JSON-LD block on that page for structured fields (provider name,
keywords).

Note: these pages appear to lazy-load additional posts on scroll. This
client captures what's present in the initial server-rendered HTML — usually
several dozen recent posts per tag, which is enough for a daily poll.
"""
import json
import re
import time

import requests
from bs4 import BeautifulSoup

HASHTAG_URL = "https://www.owlindex.com/hashtags/filters"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HydrologyRadar/1.0)"}


def fetch_hashtag_posts(hashtag: str, max_posts: int = 40):
    """Return a list of {title, summary, post_url, author} dicts for a tag."""
    resp = requests.get(
        HASHTAG_URL, params={"hashtag": hashtag}, headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    posts = []
    # Each post's "Read more" link points at /posts/single_post_view/<id>
    for link in soup.find_all("a", href=re.compile(r"/posts/single_post_view/")):
        post_url = link["href"]
        if not post_url.startswith("http"):
            post_url = "https://www.owlindex.com" + post_url

        # Title is usually the nearest preceding heading; summary is the
        # link's own text (Owlindex renders "...[Read more]" inline with
        # the summary text feeding into the link).
        heading = link.find_previous(["h5", "h4", "strong"])
        title = heading.get_text(strip=True) if heading else link.get_text(strip=True)
        summary = link.get_text(strip=True)

        posts.append({"title": title, "summary": summary, "post_url": post_url})
        if len(posts) >= max_posts:
            break

    time.sleep(0.5)
    return posts


def fetch_post_detail(post_url: str):
    """Fetch a single post page and pull schema.org JSON-LD if present.
    Returns a dict with institution/keywords/position_type when available,
    else an empty dict (caller should fall back to hashtag-page fields).
    """
    try:
        resp = requests.get(post_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        if "serviceType" in data or "provider" in data:
            provider = data.get("provider", {})
            return {
                "institution": provider.get("name", "") if isinstance(provider, dict) else "",
                "position_type": data.get("serviceType", ""),
                "keywords": data.get("keywords", ""),
            }
    return {}
