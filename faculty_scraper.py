"""
Sprint 3 client: generic scraper for faculty/lab/research-group pages.

There's no directory of "all hydrology faculty pages" to crawl, so this
works off a list of URLs you curate in config.FACULTY_SEED_URLS. For each
page it extracts:
  - email addresses (mailto: links and plain-text emails)
  - which of our KEYWORDS appear on the page
  - a content hash, so re-runs can flag when a page has changed (e.g. a new
    "now recruiting" line was added)
"""
import hashlib
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HydrologyRadar/1.0)"}
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def fetch_and_parse(url: str):
    """Returns dict: page_title, text, emails (list), content_hash."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else url

    # Strip nav/script/style noise before extracting text
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    emails = set(EMAIL_RE.findall(text))
    for a in soup.find_all("a", href=re.compile(r"^mailto:")):
        emails.add(a["href"].replace("mailto:", "").split("?")[0])

    content_hash = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()

    return {
        "page_title": page_title,
        "text": text,
        "emails": sorted(emails),
        "content_hash": content_hash,
    }
