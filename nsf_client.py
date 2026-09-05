"""
Thin client for the public NSF Award Search API.
No API key required. Docs: https://resources.research.gov/common/webapi/awardapisearch-v1.htm
"""
import time
import requests

BASE_URL = "https://api.nsf.gov/services/v1/awards.json"

# Note: we deliberately don't pass printFields. Without it, the NSF API
# already returns the full record (id, title, awardeeName, piFirstName,
# piLastName, fundsObligatedAmt, primaryProgram, startDate, date,
# abstractText, etc.) — confirmed against the live API. That's simpler and
# avoids any edge cases with comma-encoded query params.


def search_awards(keyword: str, max_pages: int = 4, rpp: int = 25):
    """Yield raw award dicts from the NSF API for a given keyword.
    Pages until max_pages reached or the API returns fewer than `rpp` results.
    """
    for page in range(max_pages):
        offset = page * rpp + 1  # NSF API offset is 1-indexed
        params = {
            "keyword": keyword,
            "rpp": rpp,
            "offset": offset,
        }
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        awards = data.get("response", {}).get("award", [])
        if not awards:
            break
        for a in awards:
            yield a
        if len(awards) < rpp:
            break
        time.sleep(0.5)  # be polite to the API
