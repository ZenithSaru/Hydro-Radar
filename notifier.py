import os
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(text: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        TELEGRAM_API.format(token=token),
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
