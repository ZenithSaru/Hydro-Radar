"""
Sprint 6: Recruitment Intelligence.

Looks at the awards table (built by Sprint 1) for PIs whose most recent
matched NSF award is both recent and large — a reasonable proxy for "just
got funded, probably hiring." Optionally adds a recent-publication count
from Semantic Scholar as a secondary signal.

IMPORTANT: `recruiting_score` here is a transparent, hand-tuned heuristic
(recency + award size + publication activity), not a trained probability
model. Treat it as a ranking signal to prioritize outreach, not a percentage
guarantee anyone is recruiting.

Run manually:
    python analyze_recruitment.py [--dry-run]
"""
import datetime
import sys
import time

import db
import recruitment
from config import (
    RECRUITMENT_AWARD_WINDOW_DAYS, RECRUITMENT_MIN_AWARD_USD,
    USE_SEMANTIC_SCHOLAR, AMOUNT_BONUS,
)
from notifier import send_telegram


def parse_date(s):
    try:
        return datetime.datetime.strptime(s, "%m/%d/%Y")
    except (ValueError, TypeError):
        return None


def amount_score(amount_usd):
    for threshold, bonus in sorted(AMOUNT_BONUS, reverse=True):
        if amount_usd and amount_usd >= threshold:
            return bonus
    return 0


def compute_score(days_ago, amount_usd, publication_count):
    recency = max(0, round(40 * (1 - days_ago / RECRUITMENT_AWARD_WINDOW_DAYS)))
    amount = amount_score(amount_usd)
    pubs = min((publication_count or 0) * 4, 20)
    return min(recency + amount + pubs, 100)


def format_signal_message(sig: dict) -> str:
    pubs = sig["publication_count"]
    pubs_line = f"\n*Recent publications:* {pubs}" if pubs is not None else ""
    return (
        f"*Recruitment Signal*  (score {sig['recruiting_score']})\n\n"
        f"*PI:* {sig['pi_name']}\n"
        f"*Institution:* {sig['institution']}\n"
        f"*Recent award:* ${sig['amount_usd']:,} on {sig['award_date']}"
        f"{pubs_line}\n\n"
        f"[View award](https://www.nsf.gov/awardsearch/showAward?AWD_ID={sig['award_id']})"
    )


def main(dry_run=False):
    today = datetime.datetime.utcnow()
    new_signals = []

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM awards WHERE matched_kw != '' ORDER BY awarded_date DESC"
        ).fetchall()

        for row in rows:
            award_date = parse_date(row["awarded_date"])
            if not award_date:
                continue
            days_ago = (today - award_date).days
            if days_ago > RECRUITMENT_AWARD_WINDOW_DAYS or days_ago < 0:
                continue
            if (row["amount_usd"] or 0) < RECRUITMENT_MIN_AWARD_USD:
                continue
            if row["pi_name"] in (None, "", "Unknown"):
                continue
            if db.is_known_signal(conn, row["pi_name"], row["institution"], row["award_id"]):
                continue

            pub_count = None
            if USE_SEMANTIC_SCHOLAR:
                pub_count = recruitment.recent_publication_count(row["pi_name"])
                time.sleep(1)  # be gentle with the free API

            score = compute_score(days_ago, row["amount_usd"], pub_count)

            sig = {
                "pi_name": row["pi_name"],
                "institution": row["institution"],
                "award_id": row["award_id"],
                "award_date": row["awarded_date"],
                "amount_usd": row["amount_usd"],
                "publication_count": pub_count,
                "recruiting_score": score,
            }
            db.insert_signal(conn, sig)
            new_signals.append(sig)

        new_signals.sort(key=lambda s: s["recruiting_score"], reverse=True)
        print(f"[recruitment] {len(new_signals)} new recruitment signal(s)")

        if not dry_run:
            for sig in new_signals:
                try:
                    send_telegram(format_signal_message(sig))
                    db.mark_signal_notified(conn, sig["pi_name"], sig["institution"], sig["award_id"])
                    time.sleep(1)
                except Exception as e:
                    print(f"[telegram] failed for {sig['pi_name']}: {e}", file=sys.stderr)
        else:
            for sig in new_signals:
                print(f" - [{sig['recruiting_score']}] {sig['pi_name']} @ {sig['institution']}")

    return new_signals


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
