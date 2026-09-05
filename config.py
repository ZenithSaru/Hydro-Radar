"""
Configuration for the Hydrology Opportunity Radar.
Edit KEYWORDS and SCORE_RULES to tune what gets flagged and how it's ranked.
"""

# Keywords matched against NSF award titles + abstracts (case-insensitive).
# An award needs at least one hit to be kept.
KEYWORDS = [
    "hydrology",
    "hydrologic",
    "water resources",
    "hydraulic engineering",
    "hydroinformatics",
    "groundwater",
    "watershed",
    "flood modeling",
    "flood forecasting",
    "flood risk",
    "InSAR",
    "land subsidence",
    "remote sensing hydrology",
    "SWAT model",
    "HEC-RAS",
    "streamflow",
    "water quality modeling",
]

# Simple additive scoring, loosely following Sprint 5 of the design brief.
# Each rule: (substring to look for in title+abstract, points).
SCORE_RULES = [
    ("hydrology", 20),
    ("hydrologic", 15),
    ("flood", 20),
    ("groundwater", 15),
    ("watershed", 15),
    ("hydraulic", 15),
    ("hydroinformatics", 20),
    ("insar", 15),
    ("subsidence", 15),
    ("water resources", 15),
]

# Award amount bonus thresholds (amount_usd_min, bonus_points)
AMOUNT_BONUS = [
    (1_000_000, 30),
    (500_000, 20),
    (250_000, 10),
]

# Position-type bonus for opportunity postings (Sprint 2/5), matched against
# title + summary text, case-insensitive substring match.
POSITION_TYPE_BONUS = [
    ("funded phd", 50),
    ("phd", 35),          # lower than "funded phd" since that's matched first
    ("research assistant", 40),
    ("graduate assistant", 35),
    ("postdoc", 20),
    ("fully funded", 15),
]

# How many NSF award pages to pull per keyword per run (25 results/page, so
# 4 pages = up to 100 most-recent matches per keyword).
MAX_PAGES_PER_KEYWORD = 4

# Only alert on awards made in the last N days (keeps the feed fresh on
# reruns and avoids re-flooding you when a new keyword is added).
LOOKBACK_DAYS = 30

# ---------------------------------------------------------------------------
# Sprint 2: Owlindex
# ---------------------------------------------------------------------------
# Owlindex hashtag feeds to scan. These are broad subject tags on the site;
# results are still filtered against KEYWORDS below before anything is
# stored or alerted. Add/remove tags at https://www.owlindex.com/hashtags/
OWLINDEX_HASHTAGS = ["Earth", "Environmental", "Civil", "Geosciences"]

# How many hashtag pages to fetch per run. Each fetch pulls ~30-40 posts.
OWLINDEX_MAX_POSTS_PER_TAG = 40

# ---------------------------------------------------------------------------
# Sprint 3: Faculty & Lab Intelligence
# ---------------------------------------------------------------------------
# Manually curated list of faculty/lab/research-group pages to monitor.
# There's no public directory of "all hydrology faculty pages" to crawl, so
# this sprint works off a list you maintain — add pages of PIs, labs, or
# departments you're tracking. The scraper re-visits these on every run and
# flags new/changed email or research-area mentions.
FACULTY_SEED_URLS = [
    # -- Land subsidence / InSAR (closest match to your thesis niche) --
    "https://globalchange.vt.edu/faculty/affiliated/shirzaei-manoochehr.html",  # Shirzaei, Virginia Tech — land subsidence, InSAR, groundwater-driven deformation
    "https://seismo.berkeley.edu/~burgmann",  # Bürgmann, UC Berkeley — Active Tectonics group, InSAR/GPS, has posted PhD openings before

    # -- Groundwater --
    "https://watershed.ucdavis.edu/people/thomas-harter",  # Harter, UC Davis — groundwater hydrology, contaminant transport

    # -- Utah Water Research Laboratory, Utah State University --
    "https://uwrl.usu.edu/people/faculty/",  # full faculty directory — broad net across the whole lab
    "https://uwrl.usu.edu/people/faculty/neilson-bethany",  # Neilson, UWRL director — watershed hydrology
    "https://uwrl.usu.edu/people/faculty/rosenberg-david",  # Rosenberg — water resources management
    "https://uwrl.usu.edu/people/faculty/lane-belize",  # Lane — rivers, watersheds, water flow
    "https://uwrl.usu.edu/people/faculty/torres-alfonso",  # Torres-Rua — remote sensing for water/irrigation
]


# ---------------------------------------------------------------------------
# Sprint 4: Google Discovery Engine
# ---------------------------------------------------------------------------
# Requires a Google Custom Search JSON API key + a Programmable Search Engine
# ID configured to search the entire web. Free tier: 100 queries/day.
# https://programmablesearchengine.google.com/  /  https://developers.google.com/custom-search/v1/overview
GOOGLE_DISCOVERY_QUERIES = [
    'site:edu "hydrology" "research assistant"',
    'site:edu "water resources" assistantship',
    'site:edu "funded phd" hydrology',
    'site:edu groundwater phd funded',
    'site:edu hydroinformatics assistantship',
    'site:edu "flood modeling" graduate assistantship',
]

# Results per query (Google CSE max is 10 per request).
GOOGLE_RESULTS_PER_QUERY = 10

# ---------------------------------------------------------------------------
# Sprint 6: Recruitment Intelligence
# ---------------------------------------------------------------------------
# A PI counts as a "recruitment signal" if their most recent matched NSF
# award is within this many days...
RECRUITMENT_AWARD_WINDOW_DAYS = 120

# ...and above this funding amount.
RECRUITMENT_MIN_AWARD_USD = 150_000

# Semantic Scholar API (free, no key required for low volume) is used to
# pull a rough recent-publication count as a secondary signal. Set to False
# to skip this (award-only scoring), e.g. if you're hitting rate limits.
USE_SEMANTIC_SCHOLAR = True

# ---------------------------------------------------------------------------
# Sprint 8: Response Pipeline (tracking + email drafts)
# ---------------------------------------------------------------------------
# Fill this in with your own info — it's what gets dropped into drafted
# outreach emails. Nothing here is sent anywhere automatically; drafts are
# only ever shown to you via Telegram for you to copy, edit, and send
# yourself.
USER_PROFILE = {
    "name": "Your Name",
    "current_program": "graduate student in Civil Engineering",  # phrase this so "a {current_program}" reads naturally
    "current_institution": "Your University",
    "research_focus": (
        "land subsidence prediction using Sentinel-1 InSAR and machine "
        "learning, with a focus on infrastructure risk screening"
    ),
    "one_line_pitch": (
        "an MS student finishing a thesis on ML-based subsidence "
        "susceptibility mapping, looking for PhD opportunities in "
        "hydrology / water resources engineering"
    ),
}

# Valid pipeline statuses, in the order they're shown in /help and the
# dashboard's Pipeline tab.
PIPELINE_STATUSES = ["new", "interested", "applied", "interview", "offer", "rejected", "skip"]

# Optional: if you set an ANTHROPIC_API_KEY secret, /draft commands use the
# Claude API to write a more tailored email instead of the plain template.
# Cheap model by default since drafts are short.
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
