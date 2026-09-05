"""
Sprint 1: Funding Intelligence Layer.

NSF API -> Keyword Filtering -> DB Storage -> Duplicate Detection -> Telegram Alert

Run manually:
    python ingest_nsf.py

Run via GitHub Actions on a schedule (see .github/workflows/nsf_radar.yml).
"""
import sys
import time
from datetime import datetime, timedelta

import db
import nsf_client
import scoring
from config import KEYWORDS, MAX_PAGES_PER_KEYWORD, LOOKBACK_DAYS
from notifier import send_telegram, format_award_message


def parse_nsf_date(s: str):
    # NSF dates come back as mm/dd/yyyy
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except (ValueError, TypeError):
        return None


def _to_str(value, sep="; "):
    """NSF sometimes returns a field (notably primaryProgram, and
    occasionally PI name fields) as a list instead of a plain string, e.g.
    when an award has multiple co-funding programs. SQLite can't store a
    Python list, so every string field going into the DB gets funneled
    through this first.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return sep.join(str(v) for v in value if v)
    return str(value)


def normalize(raw: dict) -> dict:
    award_id = _to_str(raw.get("id"))
    title = _to_str(raw.get("title"))
    abstract = _to_str(raw.get("abstractText"))
    pi_first = _to_str(raw.get("piFirstName"))
    pi_last = _to_str(raw.get("piLastName"))
    pi_name = f"{pi_first} {pi_last}".strip()
    amount_raw = raw.get("fundsObligatedAmt")
    if isinstance(amount_raw, list):
        amount_raw = amount_raw[0] if amount_raw else None
    try:
        amount_usd = int(float(amount_raw)) if amount_raw else 0
    except (ValueError, TypeError):
        amount_usd = 0

    full_text = f"{title} {abstract}"
    kws = scoring.matched_keywords(full_text)
    score = scoring.score_award(full_text, amount_usd)

    return {
        "award_id": award_id,
        "title": title,
        "institution": _to_str(raw.get("awardeeName")) or "Unknown",
        "pi_name": pi_name or "Unknown",
        "amount_usd": amount_usd,
        "program": _to_str(raw.get("primaryProgram")) or "Unknown",
        "start_date": _to_str(raw.get("startDate")),
        "awarded_date": _to_str(raw.get("date")),
        "abstract": abstract,
        "url": f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}",
        "matched_kw": ", ".join(kws),
        "score": score,
    }


def main(dry_run=False):
    cutoff = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
    new_awards = []
    seen_ids = set()

    with db.connect() as conn:
        for kw in KEYWORDS:
            print(f"[nsf] searching keyword: {kw!r}")
            try:
                for raw in nsf_client.search_awards(kw, max_pages=MAX_PAGES_PER_KEYWORD):
                    award_id = raw.get("id")
                    if not award_id or award_id in seen_ids:
                        continue
                    seen_ids.add(award_id)

                    if db.is_known(conn, award_id):
                        continue

                    award_date = parse_nsf_date(_to_str(raw.get("date")))
                    if award_date and award_date < cutoff:
                        continue

                    award = normalize(raw)
                    if not award["matched_kw"]:
                        # keyword only matched the NSF search index (e.g. PI
                        # name), not our own keyword list — skip
                        continue

                    db.insert_award(conn, award)
                    new_awards.append(award)
            except Exception as e:
                print(f"[nsf] error searching {kw!r}: {e}", file=sys.stderr)
                continue

        new_awards.sort(key=lambda a: a["score"], reverse=True)

        print(f"[nsf] {len(new_awards)} new award(s) found")

        if not dry_run:
            for award in new_awards:
                try:
                    send_telegram(format_award_message(award))
                    db.mark_notified(conn, award["award_id"])
                    time.sleep(1)  # avoid Telegram rate limits
                except Exception as e:
                    print(f"[telegram] failed for {award['award_id']}: {e}", file=sys.stderr)
        else:
            for award in new_awards:
                print(f" - [{award['score']}] {award['institution']}: {award['title'][:80]}")

    return new_awards


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
