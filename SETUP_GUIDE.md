# How to Get Your Hydrology Opportunity Radar Running

This guide assumes you've never used GitHub or written code before. Follow
it top to bottom — every step tells you exactly where to click. It'll take
about 30–45 minutes, once.

You will NOT need to install anything on your computer or use a terminal/
command line for this. Everything happens in your web browser.

---

## What you're setting up

A robot that checks for hydrology PhD/RA/GA funding opportunities every
day, and texts you on Telegram when it finds something. It runs for free
on GitHub's servers — nothing runs on your own laptop, so it works even
when your laptop is off.

---

## Part 1 — Create a GitHub account

GitHub is where the robot's code will live and run.

1. Go to **https://github.com/signup**
2. Enter an email, password, and pick a username.
3. Verify your email if asked.

If you already have a GitHub account, skip to Part 2.

---

## Part 2 — Create a Telegram bot (this is what messages you)

1. Open Telegram (app or web) and search for the user **@BotFather** —
   it has a blue checkmark, it's Telegram's official bot for making bots.
2. Start a chat with it and send: `/newbot`
3. It'll ask for a name (anything, e.g. "Hydrology Radar") and then a
   username (must end in "bot", e.g. `my_hydrology_radar_bot`).
4. BotFather replies with a **token** — a long string like
   `123456789:AAExampleTokenNotReal`. **Copy this somewhere safe.** This
   is your `TELEGRAM_BOT_TOKEN`.
5. Now find YOUR bot in Telegram (search the username you just picked) and
   send it any message, e.g. "hi". This step matters — without it, the
   bot can't message you back.
6. Get your **chat ID**: open this URL in your browser, replacing
   `<TOKEN>` with the token from step 4:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. You'll see some text with `"chat":{"id":123456789,...`. That number
   is your **chat ID** (`TELEGRAM_CHAT_ID`). Copy it too.

You now have two values saved somewhere: a **bot token** and a **chat ID**.

---

## Part 3 — Create the repository (the project's home on GitHub)

1. Log into GitHub, click the **+** icon top-right → **New repository**.
2. Name it `hydrology-radar` (or anything you like).
3. Set it to **Private** (recommended, keeps your setup to yourself) or
   Public — either works.
4. Leave everything else as default. Click **Create repository**.

---

## Part 4 — Upload the project files

1. On your computer, unzip the `hydrology-radar.zip` file I gave you
   (double-click it, or right-click → Extract).
2. Back on GitHub, on your new repository's page, click
   **"uploading an existing file"** (a blue link near the top).
3. Open the unzipped `hydrology-radar` folder on your computer. Select
   **everything inside it** (all files AND the `.github` and `docs`
   folders) and **drag them all** into the GitHub upload box in your
   browser.
   - Important: drag the *contents* of the folder, not the folder itself.
   - GitHub will preserve the folder structure (`.github/workflows/...`,
     `docs/...`) automatically as long as you drag the folders in too.
4. Scroll down, add a message like "Initial upload", and click
   **Commit changes**.
5. Refresh the page — you should see all your files listed, including a
   `.github` folder and a `docs` folder.

---

## Part 5 — Give it your Telegram credentials

1. On your repository page, click **Settings** (top menu).
2. In the left sidebar: **Secrets and variables → Actions**.
3. Click **New repository secret**.
4. Name: `TELEGRAM_BOT_TOKEN`, Value: paste the token from Part 2. Click
   **Add secret**.
5. Click **New repository secret** again.
6. Name: `TELEGRAM_CHAT_ID`, Value: paste the chat ID from Part 2. Click
   **Add secret**.

You should now see both secrets listed (values hidden, that's normal).

---

## Part 6 — Turn on the dashboard (optional but nice)

This gives you a webpage you can check anytime, in addition to Telegram
alerts.

1. **Settings → Pages** (left sidebar).
2. Under "Build and deployment" → **Source**, choose **GitHub Actions**.
3. That's it — no further steps needed here. It'll go live after your
   first run (Part 8).

---

## Part 7 — Skip or set up the optional extras

Two sprints need extra setup. **You can safely skip both for now** — the
robot will just skip those parts and run everything else normally.

### Optional: Google Discovery (finds opportunities via Google search)

1. Go to **https://console.cloud.google.com/apis/credentials**
   (you may need to create a free Google Cloud project first — follow the
   on-screen prompts, it's free).
2. Click **Create Credentials → API key**. Copy the key shown.
3. Search "Custom Search API" in the same console and click **Enable**.
4. Go to **https://programmablesearchengine.google.com/** → **Add**.
5. Under "What to search," choose **Search the entire web**. Create it.
6. Click into your new search engine → copy the **Search engine ID**.
7. Back on GitHub: **Settings → Secrets and variables → Actions → New
   repository secret**, add `GOOGLE_API_KEY` (the key from step 2) and
   `GOOGLE_CSE_ID` (the ID from step 6).

### Optional: Faculty/lab page tracking

This one skips automatically unless you edit a file yourself, which
needs the file-editing step in Part 9. You can add this anytime later —
no rush.

---

## Part 8 — Run it for the first time

1. On your repository page, click the **Actions** tab.
2. You'll see a workflow called **"Hydrology Opportunity Radar"** in the
   left sidebar — click it.
3. Click the **Run workflow** button (dropdown on the right) → **Run
   workflow** (green button).
4. Wait ~1–2 minutes, then refresh the page. You'll see a run appear with
   either a green checkmark (success) or a red X (something failed —
   see Troubleshooting below).
5. Check Telegram — you should start getting messages as it finds
   matches. **The first run can send a LOT of messages at once** since
   everything is new to it. That's expected and only happens once; after
   this, you'll only be told about *new* things.
6. If you turned on the dashboard (Part 6): go to **Settings → Pages** —
   there's now a link at the top saying "Your site is live at...". Click
   it to see your dashboard.

---

## Part 9 — What happens next

- It reruns automatically once a day — you don't need to do anything.
- Telegram messages will only arrive for genuinely new findings.
- To change what it searches for, or add faculty pages to track, you'd
  edit the `config.py` file. On GitHub: open the file → click the pencil
  (✏️) icon → make your edit → **Commit changes**. If you're not
  comfortable doing this yourself, just send me the change you want and
  I'll walk you through the exact edit.

---

## Troubleshooting

**Red X on the Actions run?**
Click the failed run, then click the step with a red X to see the error
message. The most common cause is a typo in one of the secrets (Part 5)
— double check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are exactly
right, with no extra spaces.

**No Telegram messages at all?**
Make sure you sent your bot a message first (Part 2, step 5) — Telegram
bots can't message you until you've messaged them at least once.

**Dashboard says "No data.json yet"?**
That means the workflow hasn't successfully completed a run yet — check
the Actions tab for errors first.

**Still stuck?**
Copy the error message from the Actions tab and send it to me — I'll tell
you exactly what to fix.
