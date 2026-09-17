#!/usr/bin/env python3
"""
daily_summary.py
Run at end of day via cron.
Reads today's raw push logs and rewrites them as a clean daily summary.
Uses CLAUDE.md for instructions and daily-template.md for structure.
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

# ── Load daily template ───────────────────────────────────────
template_file = VAULT_PATH / "Templates" / "daily-template.md"
if template_file.exists():
    template = template_file.read_text()
else:
    print("⚠️  daily-template.md not found, proceeding without template")
    template = ""

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
Here is the raw work log for today ({today}).
It contains entries automatically generated from git pushes.

{raw_content}

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
    "max_tokens": 1000,
    "system": instructions,
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