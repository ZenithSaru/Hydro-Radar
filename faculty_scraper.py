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

    # Grab meta description before stripping anything — academic bio pages
    # often summarize research focus there even when the body text doesn't
    # spell it out.
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag.get("content", "") if meta_desc_tag else ""

    # Image alt-text often carries keywords the visible prose doesn't (e.g.
    # a figure captioned "InSAR image of a fault" on a page whose body text
    # never actually says "InSAR"). Collect these before stripping tags.
    alt_texts = " ".join(img.get("alt", "") for img in soup.find_all("img") if img.get("alt"))

    # Strip nav/script/style noise before extracting text
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    body_text = soup.get_text(separator=" ", strip=True)
    text = " ".join(filter(None, [body_text, alt_texts, meta_desc]))

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
