"""
Sprint 8: Response Pipeline — command poller.

GitHub Actions can't run a persistent bot listener, so this polls Telegram's
getUpdates once per run instead. Scheduled to run every ~10-15 minutes (see
.github/workflows/commands.yml) — commands aren't instant, but they land
within that window.

Commands (send these as messages to your bot in Telegram):
    /status <ref> <status>   e.g. "/status 42 applied"
    /note <ref> <text>       e.g. "/note 42 emailed prof, waiting to hear back"
    /draft <ref>             generates a draft outreach email for that item
    /list [status]           lists tracked items, optionally filtered
    /help                    shows this list

Only processes messages sent from the chat matching TELEGRAM_CHAT_ID — any
other sender is ignored, so someone finding your bot's username can't drive
it.

Run manually:
    python process_commands.py
"""
import os
import sys

import db
import email_templates
from config import PIPELINE_STATUSES
from notifier import get_updates, send_telegram

HELP_TEXT = (
    "*Hydrology Radar — commands*\n\n"
    "/status <ref> <status> — update an item's status\n"
    "  valid statuses: " + ", ".join(PIPELINE_STATUSES) + "\n"
    "/note <ref> <text> — attach a note to an item\n"
    "/draft <ref> — get a draft outreach email for an item\n"
    "/list [status] — list tracked items (optionally by status)\n"
    "/help — show this message\n\n"
    "Reference numbers (#42, etc.) come from the alert messages you've "
    "already received."
)


def format_item_line(item):
    return f"#{item['ref_id']} [{item['status']}] {item['title'][:60]} — {item['institution']}"


def handle_status(conn, args):
    if len(args) < 2:
        return "Usage: /status <ref> <status>"
    try:
        ref_id = int(args[0])
    except ValueError:
        return f"'{args[0]}' isn't a valid reference number."
    status = args[1].lower()
    if status not in PIPELINE_STATUSES:
        return f"Unknown status '{status}'. Valid: {', '.join(PIPELINE_STATUSES)}"
    item = db.get_tracked_item(conn, ref_id)
    if not item:
        return f"No tracked item #{ref_id}."
    db.update_status(conn, ref_id, status)
    return f"#{ref_id} → {status}\n{item['title'][:80]}"


def handle_note(conn, args):
    if len(args) < 2:
        return "Usage: /note <ref> <text>"
    try:
        ref_id = int(args[0])
    except ValueError:
        return f"'{args[0]}' isn't a valid reference number."
    item = db.get_tracked_item(conn, ref_id)
    if not item:
        return f"No tracked item #{ref_id}."
    note_text = " ".join(args[1:])
    db.add_note(conn, ref_id, note_text)
    return f"Noted on #{ref_id}: {note_text}"


def handle_draft(conn, args):
    if len(args) < 1:
        return "Usage: /draft <ref>"
    try:
        ref_id = int(args[0])
    except ValueError:
        return f"'{args[0]}' isn't a valid reference number."
    item = db.get_tracked_item(conn, ref_id)
    if not item:
        return f"No tracked item #{ref_id}."

    item_dict = dict(item)
    draft_text = None
    source = "template"

    try:
        import ai_draft
        if ai_draft.ai_available():
            draft_text = ai_draft.generate_ai_draft(item_dict)
            source = "AI-assisted"
    except Exception as e:
        print(f"[commands] AI draft failed, falling back to template: {e}", file=sys.stderr)

    if not draft_text:
        draft_text = email_templates.draft_email(item_dict)

    return f"*Draft for #{ref_id}* ({source}) — copy, edit, and send yourself:\n\n{draft_text}"


def handle_list(conn, args):
    status_filter = args[0].lower() if args else None
    if status_filter and status_filter not in PIPELINE_STATUSES:
        return f"Unknown status '{status_filter}'. Valid: {', '.join(PIPELINE_STATUSES)}"
    items = db.list_tracked(conn, status_filter)
    if not items:
        return "Nothing tracked yet." if not status_filter else f"Nothing with status '{status_filter}'."
    lines = [format_item_line(i) for i in items[:25]]
    header = f"*Tracked items{' — ' + status_filter if status_filter else ''}* ({len(items)} total, showing up to 25)\n\n"
    return header + "\n".join(lines)


def dispatch(conn, text: str):
    text = text.strip()
    if not text.startswith("/"):
        return None  # not a command, ignore silently
    parts = text.split()
    cmd = parts[0].lower().split("@")[0]  # strip "@botname" if present
    args = parts[1:]

    if cmd == "/status":
        return handle_status(conn, args)
    if cmd == "/note":
        return handle_note(conn, args)
    if cmd == "/draft":
        return handle_draft(conn, args)
    if cmd == "/list":
        return handle_list(conn, args)
    if cmd in ("/help", "/start"):
        return HELP_TEXT
    return f"Unknown command '{cmd}'. Send /help for the list of commands."


def main():
    authorized_chat_id = str(os.environ["TELEGRAM_CHAT_ID"])

    with db.connect() as conn:
        last_update_id = db.get_state(conn, "last_update_id")
        offset = int(last_update_id) + 1 if last_update_id else None

        try:
            updates = get_updates(offset=offset, timeout=5)
        except Exception as e:
            print(f"[commands] failed to poll Telegram: {e}", file=sys.stderr)
            return

        print(f"[commands] {len(updates)} update(s) to process")

        highest_update_id = None
        for update in updates:
            highest_update_id = update["update_id"]
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue

            chat_id = str(message.get("chat", {}).get("id", ""))
            if chat_id != authorized_chat_id:
                print(f"[commands] ignoring message from unauthorized chat {chat_id}")
                continue

            text = message.get("text", "")
            if not text:
                continue

            print(f"[commands] processing: {text!r}")
            try:
                reply = dispatch(conn, text)
            except Exception as e:
                reply = f"Error handling that command: {e}"
                print(f"[commands] error: {e}", file=sys.stderr)

            if reply:
                try:
                    send_telegram(reply)
                except Exception as e:
                    print(f"[commands] failed to send reply: {e}", file=sys.stderr)

        if highest_update_id is not None:
            db.set_state(conn, "last_update_id", str(highest_update_id))


if __name__ == "__main__":
    main()
