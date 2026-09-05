"""
SQLite storage for the Hydrology Opportunity Radar.
Single-file database (radar.db) so it can live in the git repo and travel
with each GitHub Actions run.
"""
import sqlite3
from contextlib import contextmanager

DB_PATH = "radar.db"

SCHEMA = """
-- Sprint 1: NSF funding signals
CREATE TABLE IF NOT EXISTS awards (
    award_id      TEXT PRIMARY KEY,
    title         TEXT,
    institution   TEXT,
    pi_name       TEXT,
    amount_usd    INTEGER,
    program       TEXT,
    start_date    TEXT,
    awarded_date  TEXT,
    abstract      TEXT,
    url           TEXT,
    matched_kw    TEXT,
    score         INTEGER,
    first_seen    TEXT DEFAULT CURRENT_TIMESTAMP,
    notified      INTEGER DEFAULT 0
);

-- Sprint 2: Owlindex opportunity postings
CREATE TABLE IF NOT EXISTS opportunities (
    post_url      TEXT PRIMARY KEY,
    title         TEXT,
    institution   TEXT,
    position_type TEXT,
    summary       TEXT,
    hashtags      TEXT,
    matched_kw    TEXT,
    score         INTEGER,
    first_seen    TEXT DEFAULT CURRENT_TIMESTAMP,
    notified      INTEGER DEFAULT 0
);

-- Sprint 3: Faculty / lab intelligence (from user-curated seed URLs)
CREATE TABLE IF NOT EXISTS faculty (
    source_url    TEXT PRIMARY KEY,
    emails        TEXT,
    matched_kw    TEXT,
    page_title    TEXT,
    content_hash  TEXT,
    first_seen    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_checked  TEXT DEFAULT CURRENT_TIMESTAMP,
    last_changed  TEXT DEFAULT CURRENT_TIMESTAMP,
    notified      INTEGER DEFAULT 0
);

-- Sprint 4: Google discovery
CREATE TABLE IF NOT EXISTS discovered_urls (
    url           TEXT PRIMARY KEY,
    title         TEXT,
    snippet       TEXT,
    query         TEXT,
    matched_kw    TEXT,
    score         INTEGER,
    first_seen    TEXT DEFAULT CURRENT_TIMESTAMP,
    notified      INTEGER DEFAULT 0
);

-- Sprint 6: Recruitment intelligence (derived from awards table)
CREATE TABLE IF NOT EXISTS recruitment_signals (
    pi_name             TEXT,
    institution         TEXT,
    award_id            TEXT,
    award_date          TEXT,
    amount_usd          INTEGER,
    publication_count   INTEGER,
    recruiting_score    INTEGER,
    first_seen          TEXT DEFAULT CURRENT_TIMESTAMP,
    notified            INTEGER DEFAULT 0,
    PRIMARY KEY (pi_name, institution, award_id)
);

-- Sprint 8: response pipeline. One row per alert ever sent, across every
-- source above (denormalized on purpose — this table is self-contained so
-- commands/drafts never need to join back into the source-specific tables).
CREATE TABLE IF NOT EXISTS tracked_items (
    ref_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type   TEXT,   -- 'nsf_award' | 'owlindex' | 'recruitment_signal' | 'faculty' | 'discovered_url'
    source_key    TEXT,   -- the source table's own primary key, for reference
    title         TEXT,
    institution   TEXT,
    pi_name       TEXT,
    contact_email TEXT,
    summary       TEXT,
    url           TEXT,
    matched_kw    TEXT,
    status        TEXT DEFAULT 'new',   -- new | interested | applied | interview | offer | rejected | skip
    notes         TEXT DEFAULT '',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Sprint 8: small key/value store for the command-poller (tracks the last
-- processed Telegram update so it doesn't reprocess the same message twice).
CREATE TABLE IF NOT EXISTS bot_state (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- Sprint 1: awards -------------------------------------------------------

def is_known_award(conn, award_id):
    row = conn.execute(
        "SELECT 1 FROM awards WHERE award_id = ?", (award_id,)
    ).fetchone()
    return row is not None


def insert_award(conn, award: dict):
    conn.execute(
        """
        INSERT OR IGNORE INTO awards
            (award_id, title, institution, pi_name, amount_usd, program,
             start_date, awarded_date, abstract, url, matched_kw, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            award["award_id"], award["title"], award["institution"],
            award["pi_name"], award["amount_usd"], award["program"],
            award["start_date"], award["awarded_date"], award["abstract"],
            award["url"], award["matched_kw"], award["score"],
        ),
    )


def mark_award_notified(conn, award_id):
    conn.execute("UPDATE awards SET notified = 1 WHERE award_id = ?", (award_id,))


# Backwards-compatible aliases (Sprint 1 originally used these names)
is_known = is_known_award
mark_notified = mark_award_notified


# --- Sprint 2: opportunities (Owlindex) -------------------------------------

def is_known_opportunity(conn, post_url):
    row = conn.execute(
        "SELECT 1 FROM opportunities WHERE post_url = ?", (post_url,)
    ).fetchone()
    return row is not None


def insert_opportunity(conn, opp: dict):
    conn.execute(
        """
        INSERT OR IGNORE INTO opportunities
            (post_url, title, institution, position_type, summary,
             hashtags, matched_kw, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            opp["post_url"], opp["title"], opp["institution"],
            opp["position_type"], opp["summary"], opp["hashtags"],
            opp["matched_kw"], opp["score"],
        ),
    )


def mark_opportunity_notified(conn, post_url):
    conn.execute("UPDATE opportunities SET notified = 1 WHERE post_url = ?", (post_url,))


# --- Sprint 3: faculty -------------------------------------------------------

def get_faculty(conn, source_url):
    return conn.execute(
        "SELECT * FROM faculty WHERE source_url = ?", (source_url,)
    ).fetchone()


def upsert_faculty(conn, entry: dict, changed: bool):
    existing = get_faculty(conn, entry["source_url"])
    if existing is None:
        conn.execute(
            """
            INSERT INTO faculty
                (source_url, emails, matched_kw, page_title, content_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (entry["source_url"], entry["emails"], entry["matched_kw"],
             entry["page_title"], entry["content_hash"]),
        )
        return True  # new row
    conn.execute(
        """
        UPDATE faculty
        SET emails = ?, matched_kw = ?, page_title = ?, content_hash = ?,
            last_checked = CURRENT_TIMESTAMP,
            last_changed = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_changed END
        WHERE source_url = ?
        """,
        (entry["emails"], entry["matched_kw"], entry["page_title"],
         entry["content_hash"], 1 if changed else 0, entry["source_url"]),
    )
    return False  # existing row, possibly updated


def mark_faculty_notified(conn, source_url):
    conn.execute("UPDATE faculty SET notified = 1 WHERE source_url = ?", (source_url,))


# --- Sprint 4: discovered URLs (Google) -------------------------------------

def is_known_url(conn, url):
    row = conn.execute(
        "SELECT 1 FROM discovered_urls WHERE url = ?", (url,)
    ).fetchone()
    return row is not None


def insert_discovered_url(conn, item: dict):
    conn.execute(
        """
        INSERT OR IGNORE INTO discovered_urls
            (url, title, snippet, query, matched_kw, score)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item["url"], item["title"], item["snippet"], item["query"],
         item["matched_kw"], item["score"]),
    )


def mark_url_notified(conn, url):
    conn.execute("UPDATE discovered_urls SET notified = 1 WHERE url = ?", (url,))


# --- Sprint 6: recruitment signals ------------------------------------------

def is_known_signal(conn, pi_name, institution, award_id):
    row = conn.execute(
        "SELECT 1 FROM recruitment_signals WHERE pi_name = ? AND institution = ? AND award_id = ?",
        (pi_name, institution, award_id),
    ).fetchone()
    return row is not None


def insert_signal(conn, sig: dict):
    conn.execute(
        """
        INSERT OR IGNORE INTO recruitment_signals
            (pi_name, institution, award_id, award_date, amount_usd,
             publication_count, recruiting_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (sig["pi_name"], sig["institution"], sig["award_id"], sig["award_date"],
         sig["amount_usd"], sig["publication_count"], sig["recruiting_score"]),
    )


def mark_signal_notified(conn, pi_name, institution, award_id):
    conn.execute(
        "UPDATE recruitment_signals SET notified = 1 WHERE pi_name = ? AND institution = ? AND award_id = ?",
        (pi_name, institution, award_id),
    )


# --- Sprint 8: response pipeline --------------------------------------------

def create_tracked_item(conn, source_type, source_key, title="", institution="",
                         pi_name="", contact_email="", summary="", url="", matched_kw=""):
    """Call this right before sending a Telegram alert for any new item, from
    any sprint. Returns the ref_id to embed in the alert message (e.g. "#42")
    so the user can act on it with /status, /note, /draft commands.
    """
    cur = conn.execute(
        """
        INSERT INTO tracked_items
            (source_type, source_key, title, institution, pi_name,
             contact_email, summary, url, matched_kw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (source_type, source_key, title, institution, pi_name,
         contact_email, summary, url, matched_kw),
    )
    return cur.lastrowid


def get_tracked_item(conn, ref_id):
    return conn.execute(
        "SELECT * FROM tracked_items WHERE ref_id = ?", (ref_id,)
    ).fetchone()


def update_status(conn, ref_id, status):
    conn.execute(
        "UPDATE tracked_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ref_id = ?",
        (status, ref_id),
    )


def add_note(conn, ref_id, note):
    conn.execute(
        "UPDATE tracked_items SET notes = ?, updated_at = CURRENT_TIMESTAMP WHERE ref_id = ?",
        (note, ref_id),
    )


def list_tracked(conn, status=None):
    if status:
        return conn.execute(
            "SELECT * FROM tracked_items WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    return conn.execute(
        "SELECT * FROM tracked_items ORDER BY updated_at DESC"
    ).fetchall()


# --- Sprint 8: bot polling state ---------------------------------------------

def get_state(conn, key, default=None):
    row = conn.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_state(conn, key, value):
    conn.execute(
        "INSERT INTO bot_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
