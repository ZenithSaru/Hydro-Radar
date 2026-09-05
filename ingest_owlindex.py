"""
Sprint 2: Opportunity Discovery Layer.

Owlindex -> Opportunity Extraction -> Keyword Matching -> Ranking -> DB -> Telegram

Run manually:
    python ingest_owlindex.py [--dry-run]
"""
import sys
import time

import db
import owlindex_client
import scoring
from config import OWLINDEX_HASHTAGS, OWLINDEX_MAX_POSTS_PER_TAG
from notifier import send_telegram


def format_opportunity_message(opp: dict) -> str:
    inst = f"\n*Institution:* {opp['institution']}" if opp["institution"] else ""
    ptype = f"\n*Type:* {opp['position_type']}" if opp["position_type"] else ""
    return (
        f"*New Opportunity*  (score {opp['score']})\n"
        f"{inst}{ptype}\n"
        f"*Matched:* {opp['matched_kw']}\n\n"
        f"*{opp['title']}*\n{opp['summary'][:300]}\n\n"
        f"[View on Owlindex]({opp['post_url']})"
    )


def main(dry_run=False):
    new_opps = []

    with db.connect() as conn:
        for tag in OWLINDEX_HASHTAGS:
            print(f"[owlindex] scanning hashtag #{tag}")
            try:
                posts = owlindex_client.fetch_hashtag_posts(tag, OWLINDEX_MAX_POSTS_PER_TAG)
            except Exception as e:
                print(f"[owlindex] error fetching #{tag}: {e}", file=sys.stderr)
                continue

            for post in posts:
                if db.is_known_opportunity(conn, post["post_url"]):
                    continue

                full_text = f"{post['title']} {post['summary']}"
                kws = scoring.matched_keywords(full_text)
                if not kws:
                    continue  # not relevant to our discipline list

                detail = {}
                try:
                    detail = owlindex_client.fetch_post_detail(post["post_url"])
                except Exception:
                    pass

                combined_text = full_text + " " + detail.get("keywords", "")
                score = scoring.score_award(combined_text, 0) + scoring.score_position_type(combined_text)

                opp = {
                    "post_url": post["post_url"],
                    "title": post["title"],
                    "institution": detail.get("institution", ""),
                    "position_type": detail.get("position_type", ""),
                    "summary": post["summary"],
                    "hashtags": tag,
                    "matched_kw": ", ".join(kws),
                    "score": score,
                }
                db.insert_opportunity(conn, opp)
                new_opps.append(opp)
                time.sleep(0.3)

        new_opps.sort(key=lambda o: o["score"], reverse=True)
        print(f"[owlindex] {len(new_opps)} new opportunit(y/ies) found")

        if not dry_run:
            for opp in new_opps:
                try:
                    send_telegram(format_opportunity_message(opp))
                    db.mark_opportunity_notified(conn, opp["post_url"])
                    time.sleep(1)
                except Exception as e:
                    print(f"[telegram] failed for {opp['post_url']}: {e}", file=sys.stderr)
        else:
            for opp in new_opps:
                print(f" - [{opp['score']}] {opp['title'][:90]}")

    return new_opps


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
