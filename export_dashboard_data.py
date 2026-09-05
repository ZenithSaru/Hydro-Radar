"""
Sprint 5 + 7: pulls everything out of radar.db into one JSON file the static
dashboard (docs/index.html) reads. Also used to build the daily digest.

Run manually:
    python export_dashboard_data.py
"""
import json
import datetime

import db

OUT_PATH = "docs/data.json"


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def main():
    with db.connect() as conn:
        awards = conn.execute(
            "SELECT * FROM awards WHERE matched_kw != '' ORDER BY score DESC LIMIT 100"
        ).fetchall()
        opportunities = conn.execute(
            "SELECT * FROM opportunities ORDER BY score DESC LIMIT 100"
        ).fetchall()
        faculty = conn.execute(
            "SELECT * FROM faculty ORDER BY last_changed DESC LIMIT 100"
        ).fetchall()
        discovered = conn.execute(
            "SELECT * FROM discovered_urls ORDER BY score DESC LIMIT 100"
        ).fetchall()
        signals = conn.execute(
            "SELECT * FROM recruitment_signals ORDER BY recruiting_score DESC LIMIT 100"
        ).fetchall()

    data = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "awards": rows_to_dicts(awards),
        "opportunities": rows_to_dicts(opportunities),
        "faculty": rows_to_dicts(faculty),
        "discovered_urls": rows_to_dicts(discovered),
        "recruitment_signals": rows_to_dicts(signals),
    }

    import os
    os.makedirs("docs", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"[export] wrote {OUT_PATH}: "
          f"{len(awards)} awards, {len(opportunities)} opportunities, "
          f"{len(faculty)} faculty pages, {len(discovered)} discovered URLs, "
          f"{len(signals)} recruitment signals")
    return data


if __name__ == "__main__":
    main()
