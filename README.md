# Hydrology Opportunity Radar

Watches NSF grants, Owlindex postings, faculty/lab pages you choose to
track, and (optionally) Google for funded RA/GA/MS/PhD opportunities in
hydrology / water resources / groundwater / flood modeling / etc. Scores
everything, alerts you on Telegram with a reference number you can act on,
tracks each one through a status pipeline, drafts outreach emails, and
publishes a browsable dashboard — all running free on a GitHub Actions
schedule. No server to maintain.

All 8 sprints are implemented (7 from the original design brief, plus a
Sprint 8 "response pipeline" added afterward). A few of them have honest
limitations described below — read those before you expect magic.

## Architecture

```
NSF Awards API ──┐
Owlindex scrape ──┤
Faculty pages ────┼──► keyword filter + scoring ──► radar.db (SQLite) ──┬──► Telegram alerts (with #ref)
Google (optional) ┘                                                     ├──► Daily digest (Telegram)
                                                                         ├──► tracked_items (pipeline)
awards table ──► recruitment heuristic ──► recruitment_signals table ───┘         │
                                                                                   ├──► /status /note /draft via Telegram (polled)
                                                                                   └──► docs/data.json ──► GitHub Pages dashboard (Pipeline tab)
```

Everything lives in one SQLite file (`radar.db`) that's committed back to
the repo after each run, so state persists across GitHub Actions runs
without a database server.

## What each sprint actually does

| Sprint | Script | Status |
|---|---|---|
| 1. NSF funding intelligence | `ingest_nsf.py` | Full — public API, no key needed |
| 2. Owlindex opportunity discovery | `ingest_owlindex.py` | Full — scrapes hashtag feeds + post detail pages |
| 3. Faculty & lab intelligence | `monitor_faculty.py` | **Works off a list you curate** (`config.FACULTY_SEED_URLS`) — there's no public directory of "all hydrology faculty pages" to crawl automatically |
| 4. Google discovery | `discover_google.py` | **Needs your own Google API key** (free tier, see setup below). Scores against search snippets, doesn't crawl full pages |
| 5. Ranking & prioritization | folded into each sprint's `scoring.py` calls + `export_dashboard_data.py` | Full |
| 6. Recruitment intelligence | `analyze_recruitment.py` | **Heuristic score, not a trained model.** Combines award recency + amount + a rough Semantic Scholar publication count. Treat it as a ranking signal, not a probability |
| 7. Dashboard & analytics | `docs/index.html` + `export_dashboard_data.py` | Full — static site on GitHub Pages, updated each run |
| 8. Response pipeline | `process_commands.py`, `email_templates.py`, `ai_draft.py` | Full — status tracking + drafted (not sent) emails, via Telegram commands, polled every ~15 min |

## One-time setup

### 1. Push this to a GitHub repo

```bash
cd hydrology-radar
git init
git add .
git commit -m "Hydrology Opportunity Radar — all sprints"
git branch -M main
git remote add origin https://github.com/<you>/hydrology-radar.git
git push -u origin main
```

### 2. Add Telegram credentials as repo secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | from @BotFather |
| `TELEGRAM_CHAT_ID` | message the bot once, then check `https://api.telegram.org/bot<TOKEN>/getUpdates` |

### 3. (Optional) Enable Sprint 4 — Google discovery

Google retired "Search the entire web" for new Programmable Search Engines
in early 2026 — new engines must specify actual domains (up to 50), and
bare TLD wildcards like `*.edu/*` are rejected outright. So this now works
by listing specific university domains instead:

1. Create an API key at https://console.cloud.google.com/apis/credentials (enable the "Custom Search API")
2. Create a Programmable Search Engine at https://programmablesearchengine.google.com/
3. Under **Sites to search → Add**, paste a list of university domains as
   `*.domain.edu/*` patterns, one per line (Google accepts a multi-line
   paste here). A ~40-domain starter list covering major US water-resources
   programs is available on request — ask and I'll generate one for you,
   or reuse the one already given to you in chat.
4. Copy the **Search engine ID** from the engine's Overview page
5. Add two repo secrets: `GOOGLE_API_KEY` and `GOOGLE_CSE_ID`

Skip this and Sprint 4 just no-ops (the pipeline logs a note and moves on)
— free tier is 100 queries/day, plenty for the ~6 queries/day this runs.

### 4. (Optional) Populate Sprint 3 — faculty/lab pages to watch

Edit `config.py`:

```python
FACULTY_SEED_URLS = [
    "https://www.example.edu/faculty/jane-smith",
    "https://waterlab.example.edu/people",
]
```

Leave it empty and Sprint 3 just skips with a note.

### 5. Fill in your profile (for Sprint 8's email drafts)

Edit `config.py`'s `USER_PROFILE` dict with your real name, program,
institution, and a one-line pitch. This is what gets dropped into drafted
outreach emails — nothing is sent anywhere automatically, drafts only ever
come back to you on Telegram to copy, edit, and send yourself.

### 6. (Optional) Enable AI-assisted drafts

Without this, `/draft` uses a plain mail-merge template (still fully
functional, just generic). To get better, more tailored drafts:

1. Get an API key from https://console.anthropic.com/
2. Add a repo secret named `ANTHROPIC_API_KEY`

If it's missing or a call fails for any reason, `/draft` automatically
falls back to the template — you'll never get an error instead of a draft.

### 7. Enable GitHub Pages (for the dashboard)

**Settings → Pages → Source → GitHub Actions.** The workflow's
`deploy-pages` job publishes `docs/` there automatically after each run.

### 8. Seed the database (recommended)

Without this, your first scheduled run alerts you on everything currently
matching — could be 50+ Telegram messages at once. Populate the DB quietly
first:

```bash
pip install -r requirements.txt
python ingest_nsf.py --dry-run
python ingest_owlindex.py --dry-run
python monitor_faculty.py --dry-run      # only if you filled in FACULTY_SEED_URLS
python discover_google.py --dry-run      # only if you set up Google secrets locally
python analyze_recruitment.py --dry-run
python export_dashboard_data.py
git add radar.db docs/data.json
git commit -m "Seed database"
git push
```

### 9. That's it

Two workflows run on their own:
- **"Hydrology Opportunity Radar"** — daily at 13:00 UTC, does the actual discovery
- **"Hydrology Radar - Command Poller"** — every ~15 minutes, checks for
  Telegram commands and replies

Trigger either manually any time from the **Actions** tab.

## Talking to the pipeline (Sprint 8)

Every alert you get includes a reference number, e.g. `Ref: #42`. Reply to
your bot on Telegram (not a comment on the message — just send it a new
message) with any of:

```
/status 42 interested      valid: new, interested, applied, interview, offer, rejected, skip
/note 42 emailed prof, waiting to hear back
/draft 42                  drafts an outreach email for item #42
/list                      lists everything you're tracking
/list applied              lists only items with that status
/help                      shows this cheat sheet
```

Replies aren't instant — the poller checks every ~15 minutes (GitHub's
scheduler can add its own delay on top, especially on the free tier), so
expect a reply within 15-30 minutes, not seconds.

## Tuning it

Everything lives in `config.py`:

- `KEYWORDS` — what counts as a match everywhere (title/abstract/page text)
- `SCORE_RULES`, `AMOUNT_BONUS`, `POSITION_TYPE_BONUS` — scoring weights
- `LOOKBACK_DAYS`, `RECRUITMENT_AWARD_WINDOW_DAYS`, `RECRUITMENT_MIN_AWARD_USD` — recency/threshold knobs
- `OWLINDEX_HASHTAGS`, `GOOGLE_DISCOVERY_QUERIES`, `FACULTY_SEED_URLS` — what to watch

## Running things individually

Every script takes `--dry-run` (prints instead of sending Telegram alerts):

```bash
python ingest_nsf.py --dry-run
python ingest_owlindex.py --dry-run
python monitor_faculty.py --dry-run
python discover_google.py --dry-run
python analyze_recruitment.py --dry-run
python daily_digest.py --dry-run
python export_dashboard_data.py     # always writes docs/data.json, no Telegram involved
python process_commands.py          # checks for + replies to Telegram commands once (no --dry-run; it's read-then-reply by nature)
```

## Known limitations (read this)

- **Owlindex has no public API.** This scrapes the rendered hashtag pages,
  which appear to lazy-load more posts on scroll — each run captures the
  most recent batch per tag (a few dozen posts), which is enough for a
  daily poll but isn't exhaustive history.
- **Sprint 3 requires manual curation.** There's no way to auto-discover
  "all faculty pages in hydrology" — you feed it URLs.
- **Sprint 6's recruiting_score is a heuristic**, not a validated model. The
  award-based part (a PI just got NSF money) is solid; the publication
  count is a rough name-search against Semantic Scholar and can misfire on
  common names.
- **Sprint 4 needs your own Google API credentials** and only scores
  against search snippets, not full page crawls.
- **Sprint 8's drafts need a human pass before sending.** The template
  version is generic mail-merge; the AI version is better but still
  reflects only what's in the alert (title/abstract/snippet) — it doesn't
  know anything about the professor beyond that. Neither one ever sends
  anything; you always copy/paste yourself.
- **Command replies aren't instant.** The poller runs every ~15 minutes,
  and GitHub's free-tier scheduler can add its own delay on top.

None of this is fake — every script here runs against the real, live APIs
and was checked against them while building. The limitations above are
inherent to the sources, not shortcuts.
