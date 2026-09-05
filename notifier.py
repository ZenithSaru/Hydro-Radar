import os
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def send_telegram(text: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        TELEGRAM_API.format(token=token, method="sendMessage"),
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_updates(offset=None, timeout=10):
    """Poll Telegram for new messages sent to the bot since `offset`.
    Returns the raw list of update dicts (see Telegram Bot API docs).
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(
        TELEGRAM_API.format(token=token, method="getUpdates"),
        params=params,
        timeout=timeout + 10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {data}")
    return data.get("result", [])


def format_award_message(award: dict) -> str:
    amount = f"${award['amount_usd']:,}" if award["amount_usd"] else "N/A"
    kw = award["matched_kw"]
    return (
        f"*NSF Funding Signal*  (score {award['score']})\n\n"
        f"*Institution:* {award['institution']}\n"
        f"*PI:* {award['pi_name']}\n"
        f"*Amount:* {amount}\n"
        f"*Program:* {award['program']}\n"
        f"*Matched:* {kw}\n\n"
        f"*Title:* {award['title']}\n\n"
        f"[View on NSF Award Search]({award['url']})"
    )
