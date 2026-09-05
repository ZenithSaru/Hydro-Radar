"""
Sprint 5 + 7: "Generate Daily Digest" step. Sends ONE consolidated Telegram
message summarizing the top items across all sources, instead of (or in
addition to) the per-item alerts each sprint script already sends.

Run manually:
    python daily_digest.py [--dry-run]
"""
import sys

import db
from notifier import send_telegram


def top(rows, key, n=5):
    return sorted(rows, key=lambda r: r[key] or 0, reverse=True)[:n]


def main(dry_run=False):
    with db.connect() as conn:
        awards = conn.execute(
            "SELECT * FROM awards WHERE matched_kw != ''"
        ).fetchall()
        opportunities = conn.execute("SELECT * FROM opportunities").fetchall()
        signals = conn.execute("SELECT * FROM recruitment_signals").fetchall()

    lines = ["*Hydrology Opportunity Radar — Daily Digest*\n"]

    lines.append(f"📊 {len(awards)} matched NSF awards, "
                 f"{len(opportunities)} Owlindex opportunities tracked, "
                 f"{len(signals)} recruitment signals on file.\n")

    top_opps = top(opportunities, "score")
    if top_opps:
        lines.append("*Top opportunities:*")
        for o in top_opps:
            lines.append(f"  • [{o['score']}] {o['title'][:70]}")
        lines.append("")

    top_signals = top(signals, "recruiting_score")
    if top_signals:
        lines.append("*Top recruitment signals:*")
        for s in top_signals:
            lines.append(f"  • [{s['recruiting_score']}] {s['pi_name']} @ {s['institution']}")
        lines.append("")

    top_awards = top(awards, "score")
    if top_awards:
        lines.append("*Top funding signals:*")
        for a in top_awards:
            lines.append(f"  • [{a['score']}] {a['institution']}: {a['title'][:60]}")

    message = "\n".join(lines)

    if dry_run:
        print(message)
    else:
        try:
            send_telegram(message)
        except Exception as e:
            print(f"[telegram] digest send failed: {e}", file=sys.stderr)

    return message


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
