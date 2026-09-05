"""
Sprint 8 (optional): AI-personalized email drafts via the Anthropic API.

Only used if you set an ANTHROPIC_API_KEY secret — otherwise process_commands.py
falls back to the plain template in email_templates.py, which needs no key at
all. Nothing here ever sends an email; it only generates text that gets
handed back to you on Telegram to review, edit, and send yourself.
"""
import os
import requests

from config import USER_PROFILE, ANTHROPIC_MODEL

API_URL = "https://api.anthropic.com/v1/messages"


def ai_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def generate_ai_draft(item: dict) -> str:
    """Raises on any failure — caller should catch and fall back to the
    template version. Never silently returns something misleading.
    """
    api_key = os.environ["ANTHROPIC_API_KEY"]  # KeyError if missing = caller's bug, not ours
    profile = USER_PROFILE

    is_funding_signal = item.get("source_type") in ("nsf_award", "recruitment_signal")
    context = (
        f"A newly funded NSF award: \"{item.get('title')}\" at {item.get('institution')}, "
        f"PI: {item.get('pi_name') or 'unknown'}."
        if is_funding_signal else
        f"A posted opportunity: \"{item.get('title')}\" at {item.get('institution')}."
    )

    prompt = f"""Write a short, professional outreach email (under 200 words, plus a subject line)
from a prospective graduate student to a professor, based on this opportunity:

{context}
Summary/abstract: {(item.get('summary') or '')[:500]}
Matched research areas: {item.get('matched_kw', '')}

About the sender:
- Name: {profile.get('name')}
- Current program: {profile.get('current_program')} at {profile.get('current_institution')}
- Research focus: {profile.get('research_focus')}
- One-line pitch: {profile.get('one_line_pitch')}

{"This is a cold inquiry about a funding signal — the professor hasn't posted an opening, so ask whether they anticipate openings, don't assume there's a specific listed position." if is_funding_signal else "This is a response to an actual posted opening — reference it directly."}

Output ONLY the email (starting with "Subject: ..."), no preamble, no commentary."""

    resp = requests.post(
        API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    draft = "\n".join(text_blocks).strip()
    if not draft:
        raise ValueError("Anthropic API returned no text content")
    return draft
