"""
Sprint 4: Google Discovery Engine.

GOOGLE_DISCOVERY_QUERIES (config.py) -> Google Custom Search -> New URLs
-> keyword/score against title+snippet -> DB -> Telegram

This deliberately does NOT crawl every discovered page's full content (that's
a much bigger, slower operation and risks hammering random university
servers) — it scores against the search result's own title + snippet, which
Google already extracts from the page. If something looks promising, open it.

Run manually:
    python discover_google.py [--dry-run]

Skips silently (with a note) if GOOGLE_API_KEY / GOOGLE_CSE_ID aren't set,
so this sprint is optional and won't break the rest of the pipeline.
"""
import sys
import time

import db
import google_discovery
import scoring
from config import GOOGLE_DISCOVERY_QUERIES, GOOGLE_RESULTS_PER_QUERY
from notifier import send_telegram


def format_discovery_message(item: dict) -> str:
    return (
        f"*New Google Discovery*  (score {item['score']})\n\n"
        f"*Matched:* {item['matched_kw']}\n"
        f"*Query:* {item['query']}\n\n"
        f"*{item['title']}*\n{item['snippet']}\n\n"
        f"{item['url']}"
    )


def main(dry_run=False):
    new_items = []

    with db.connect() as conn:
        for query in GOOGLE_DISCOVERY_QUERIES:
            print(f"[google] searching: {query!r}")
            try:
                results = google_discovery.search(query, GOOGLE_RESULTS_PER_QUERY)
            except google_discovery.GoogleSearchNotConfigured as e:
                print(f"[google] skipping Sprint 4 — {e}")
                return []
            except Exception as e:
                print(f"[google] error searching {query!r}: {e}", file=sys.stderr)
                continue

            for r in results:
                if db.is_known_url(conn, r["url"]):
                    continue
                text = f"{r['title']} {r['snippet']}"
                kws = scoring.matched_keywords(text)
                if not kws:
                    continue

                score = scoring.score_award(text, 0) + scoring.score_position_type(text)
                item = {
                    "url": r["url"],
                    "title": r["title"],
                    "snippet": r["snippet"],
                    "query": query,
                    "matched_kw": ", ".join(kws),
                    "score": score,
                }
                db.insert_discovered_url(conn, item)
                new_items.append(item)

            time.sleep(0.5)

        new_items.sort(key=lambda i: i["score"], reverse=True)
        print(f"[google] {len(new_items)} new URL(s) found")

        if not dry_run:
            for item in new_items:
                try:
                    send_telegram(format_discovery_message(item))
                    db.mark_url_notified(conn, item["url"])
                    time.sleep(1)
                except Exception as e:
                    print(f"[telegram] failed for {item['url']}: {e}", file=sys.stderr)
        else:
            for item in new_items:
                print(f" - [{item['score']}] {item['title'][:90]}")

    return new_items


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
