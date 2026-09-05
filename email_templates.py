"""
Sprint 8: template-based outreach email drafts.

These are plain mail-merge templates — no AI involved, no API key needed.
They're deliberately generic and will need a personal pass before sending,
but they save you from starting from a blank page. See ai_draft.py for an
optional, better-personalized version if you add an ANTHROPIC_API_KEY.
"""
from config import USER_PROFILE

# Funding-signal sources (nsf_award, recruitment_signal): the PI hasn't
# necessarily posted an opening, so this is a "do you have room" inquiry.
FUNDING_SIGNAL_TEMPLATE = """Subject: Prospective PhD student — {research_focus_short}

Dear Dr. {pi_last_name},

My name is {name}, a {current_program} at {current_institution}. I came across \
your recently funded work on "{title}" and wanted to reach out directly, as it \
aligns closely with my own background in {research_focus}.

I'm {one_line_pitch}. I'd welcome the chance to learn whether you anticipate \
openings for a graduate student on this or related work, and I'd be glad to \
share my CV and a writing sample if that's useful.

Thank you for your time — I know funding-season inboxes get busy.

Best regards,
{name}
{current_program}, {current_institution}
"""

# Posted-opening sources (owlindex, discovered_url): there's an actual listing
# to respond to.
POSTED_OPENING_TEMPLATE = """Subject: Application inquiry — {title}

Dear Hiring Committee{pi_name_suffix},

I'm writing regarding the opening "{title}" at {institution}. My name is \
{name}, a {current_program} at {current_institution}, and I'm {one_line_pitch}.

{summary_line}I believe my background in {research_focus} would translate well \
to this position, and I'd welcome the opportunity to discuss it further.

I've attached my CV for your review, and I'm happy to provide additional \
materials on request.

Best regards,
{name}
{current_program}, {current_institution}
"""


def _first_last(pi_name: str):
    parts = (pi_name or "").split()
    if not parts:
        return "", ""
    return parts[0], parts[-1]


def draft_email(item: dict) -> str:
    """item is a tracked_items row (or equivalent dict) with at least:
    source_type, title, institution, pi_name, summary, matched_kw
    """
    profile = USER_PROFILE
    research_focus = profile.get("research_focus", "")
    research_focus_short = research_focus.split(",")[0] if research_focus else "graduate research"

    _, pi_last = _first_last(item.get("pi_name", ""))
    pi_name_suffix = f" (attn: Dr. {pi_last})" if pi_last else ""

    summary = (item.get("summary") or "").strip()
    summary_line = f"{summary[:300]}\n\n" if summary else ""

    fields = {
        "name": profile.get("name", "Your Name"),
        "current_program": profile.get("current_program", ""),
        "current_institution": profile.get("current_institution", ""),
        "research_focus": research_focus,
        "research_focus_short": research_focus_short,
        "one_line_pitch": profile.get("one_line_pitch", ""),
        "title": item.get("title", ""),
        "institution": item.get("institution", "the institution"),
        "pi_last_name": pi_last or "[PI last name]",
        "pi_name_suffix": pi_name_suffix,
        "summary_line": summary_line,
    }

    if item.get("source_type") in ("nsf_award", "recruitment_signal"):
        return FUNDING_SIGNAL_TEMPLATE.format(**fields)
    return POSTED_OPENING_TEMPLATE.format(**fields)
