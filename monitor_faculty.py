"""
Sprint 3: Faculty & Laboratory Intelligence.

FACULTY_SEED_URLS (config.py) -> Email Extraction -> Research Area Extraction
-> DB -> Recruitment Signals (new page, or a change since last check)

Run manually:
    python monitor_faculty.py [--dry-run]
"""
import sys
import time

import db
import faculty_scraper
import scoring
from config import FACULTY_SEED_URLS
from notifier import send_telegram


def format_faculty_message(url: str, parsed: dict, kws: list, is_new: bool) -> str:
    header = "New Faculty/Lab Page Tracked" if is_new else "Faculty/Lab Page Changed"
    emails = ", ".join(parsed["emails"]) or "none found"
    return (
        f"*{header}*\n\n"
        f"*Page:* {parsed['page_title']}\n"
        f"*Matched:* {', '.join(kws) or 'none'}\n"
        f"*Emails:* {emails}\n\n"
        f"{url}"
    )


def main(dry_run=False):
    if not FACULTY_SEED_URLS:
        print("[faculty] FACULTY_SEED_URLS is empty in config.py — nothing to check. "
              "Add faculty/lab page URLs there to use this sprint.")
        return []

    alerts = []
    with db.connect() as conn:
        for url in FACULTY_SEED_URLS:
            print(f"[faculty] checking {url}")
            try:
                parsed = faculty_scraper.fetch_and_parse(url)
            except Exception as e:
                print(f"[faculty] error fetching {url}: {e}", file=sys.stderr)
                continue

            kws = scoring.matched_keywords(parsed["text"])
            existing = db.get_faculty(conn, url)
            changed = existing is not None and existing["content_hash"] != parsed["content_hash"]

            is_new = db.upsert_faculty(
                conn,
                {
                    "source_url": url,
                    "emails": ", ".join(parsed["emails"]),
                    "matched_kw": ", ".join(kws),
                    "page_title": parsed["page_title"],
                    "content_hash": parsed["content_hash"],
                },
                changed,
            )

            if (is_new or changed) and kws:
                alerts.append((url, parsed, kws, is_new))

            time.sleep(0.3)

        print(f"[faculty] {len(alerts)} new/changed page(s) worth flagging")

        if not dry_run:
            for url, parsed, kws, is_new in alerts:
                try:
                    send_telegram(format_faculty_message(url, parsed, kws, is_new))
                    db.mark_faculty_notified(conn, url)
                    time.sleep(1)
                except Exception as e:
                    print(f"[telegram] failed for {url}: {e}", file=sys.stderr)
        else:
            for url, parsed, kws, is_new in alerts:
                tag = "NEW" if is_new else "CHANGED"
                print(f" - [{tag}] {parsed['page_title']} — {url}")

    return alerts


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
