from config import KEYWORDS, SCORE_RULES, AMOUNT_BONUS, POSITION_TYPE_BONUS


def matched_keywords(text: str):
    text_l = text.lower()
    return [kw for kw in KEYWORDS if kw.lower() in text_l]


def score_award(text: str, amount_usd: int):
    text_l = text.lower()
    score = 0
    for term, points in SCORE_RULES:
        if term in text_l:
            score += points
    for threshold, bonus in sorted(AMOUNT_BONUS, reverse=True):
        if amount_usd and amount_usd >= threshold:
            score += bonus
            break
    return score


def score_position_type(text: str):
    """Bonus points for position-type language (Sprint 2/5): funded PhD,
    research assistant, etc. Only the first (highest-priority) match in
    POSITION_TYPE_BONUS counts, since e.g. "funded phd" and "phd" would
    otherwise double-count the same posting.
    """
    text_l = text.lower()
    for term, points in POSITION_TYPE_BONUS:
        if term in text_l:
            return points
    return 0
