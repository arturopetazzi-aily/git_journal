#!/usr/bin/env python3
"""
daily_summary.py
Run at end of day via cron.
Reads today's raw push logs and rewrites them as a clean daily summary.
"""

import os
import sys
import requests
from datetime import datetime
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

AILY_API_KEY = os.getenv("AILY_API_KEY")
AILY_GATEWAY = os.getenv("AILY_GATEWAY_URL")
AILY_MODEL   = os.getenv("AILY_MODEL")
VAULT_PATH   = Path(os.getenv("VAULT_PATH"))

# ── Read today's log ──────────────────────────────────────────
today      = datetime.now().strftime("%Y-%m-%d")
daily_dir  = VAULT_PATH / "Daily"
daily_file = daily_dir / f"{today}.md"

if not daily_file.exists():
    print(f"ℹ️  No log found for today ({today}). Nothing to summarize.")
    sys.exit(0)

raw_content = daily_file.read_text()

if not raw_content.strip():
    print("ℹ️  Today's log is empty. Nothing to summarize.")
    sys.exit(0)

print(f"📖 Reading today's log: {daily_file}")

# ── Build the prompt ──────────────────────────────────────────
prompt = f"""
Here is my raw work log for today ({today}). 
It contains entries automatically generated from git pushes throughout the day.

{raw_content}

Please rewrite this as a clean, structured daily summary using exactly this format:

# Daily Log - {today}
tags: [daily, ai-coding]

## 📊 Day at a Glance
- Repos touched: <list repo names>
- Total pushes: <count>
- Main focus: <one line>

## 🔨 Work Done
<group the commits by repo, summarize what was actually accomplished,
not just list commit messages. Write it as a human would.>

## 🧠 Notes & Observations
<any patterns, interesting things, or inferences you can make from the commits>

## ⏭️ Possible Next Steps
<based on the work done today, what likely comes next>

Keep it concise and professional. Do not add anything that is not inferable from the commits.
"""

# ── Call Aily gateway ─────────────────────────────────────────
headers = {
    "Authorization": f"Bearer {AILY_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": AILY_MODEL,
    "max_tokens": 1000,
    "messages": [
        {"role": "user", "content": prompt}
    ]
}

try:
    print("🤖 Asking Claude to summarize...")
    response = requests.post(
        f"{AILY_GATEWAY}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    summary = response.json()["choices"][0]["message"]["content"].strip()

    # Overwrite today's file with the clean summary
    daily_file.write_text(summary)
    print(f"✅ Daily summary written to {daily_file}")

except requests.exceptions.RequestException as e:
    print(f"❌ Gateway error: {e}")
    try:
        print(f"Response: {e.response.text}")
    except:
        pass
    print("⚠️  Original log preserved unchanged.")
    sys.exit(1)