#!/usr/bin/env python3
"""
weekly_summary.py
Run every Friday at 5pm via cron.
Reads all daily logs from the current week and writes a weekly summary.
Uses CLAUDE.md for instructions and weekly-template.md for structure.
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from pathlib import Path

# ── Load .env manually ────────────────────────────────────────
env_path = Path.home() / "dev_journal_scripts" / ".env"

if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
else:
    print(f"❌ .env file not found at {env_path}")
    sys.exit(1)

AILY_API_KEY  = os.getenv("AILY_API_KEY")
AILY_GATEWAY  = os.getenv("AILY_GATEWAY_URL")
AILY_MODEL    = os.getenv("AILY_MODEL")
VAULT_PATH    = Path(os.getenv("VAULT_PATH"))
SCRIPTS_PATH  = Path.home() / "dev_journal_scripts"

# ── Load CLAUDE.md instructions ───────────────────────────────
claude_md = SCRIPTS_PATH / "CLAUDE.md"
if claude_md.exists():
    instructions = claude_md.read_text()
else:
    print("⚠️  CLAUDE.md not found, proceeding without instructions")
    instructions = ""

# ── Load weekly template ──────────────────────────────────────
template_file = VAULT_PATH / "Templates" / "weekly-template.md"
if template_file.exists():
    template = template_file.read_text()
else:
    print("⚠️  weekly-template.md not found, proceeding without template")
    template = ""

# ── Find this week's Monday to Friday ────────────────────────
today     = datetime.now()
monday    = today - timedelta(days=today.weekday())
week_days = [monday + timedelta(days=i) for i in range(5)]
week_num  = today.strftime("%Y-W%W")

print(f"📅 Collecting daily logs for week {week_num}...")

# ── Read all daily logs from this week ───────────────────────
daily_logs = []

for day in week_days:
    date_str   = day.strftime("%Y-%m-%d")
    daily_file = VAULT_PATH / "Daily" / f"{date_str}.md"

    if daily_file.exists():
        content = daily_file.read_text().strip()
        if content:
            daily_logs.append(f"### {date_str}\n{content}")
            print(f"  ✅ Found: {date_str}")
    else:
        print(f"  ⚠️  No log for: {date_str}")

if not daily_logs:
    print("ℹ️  No daily logs found for this week. Nothing to summarize.")
    sys.exit(0)

combined_logs = "\n\n---\n\n".join(daily_logs)

# ── Build the prompt ──────────────────────────────────────────
prompt = f"""
Here are the daily work logs for the week of {week_num}.

{combined_logs}

---

Use this template as the structure for your response:

{template}

Replace all {{{{placeholder}}}} fields with the actual content.
Follow the writing instructions provided in the system prompt exactly.
Do not add sections that are not in the template.
If a section has no meaningful content, write "None" rather than omitting it.
"""

# ── Call Aily gateway ─────────────────────────────────────────
headers = {
    "Authorization": f"Bearer {AILY_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": AILY_MODEL,
    "max_tokens": 1500,
    "system": instructions,
    "messages": [
        {"role": "user", "content": prompt}
    ]
}

try:
    print("🤖 Asking Claude to write weekly review...")
    response = requests.post(
        f"{AILY_GATEWAY}/chat/completions",
        headers=headers,
        json=payload,
        timeout=45
    )
    response.raise_for_status()
    summary = response.json()["choices"][0]["message"]["content"].strip()

    weekly_dir  = VAULT_PATH / "Weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    weekly_file = weekly_dir / f"{week_num}.md"

    weekly_file.write_text(summary)
    print(f"✅ Weekly review written to {weekly_file}")

except requests.exceptions.RequestException as e:
    print(f"❌ Gateway error: {e}")
    try:
        print(f"Response: {e.response.text}")
    except:
        pass
    sys.exit(1)