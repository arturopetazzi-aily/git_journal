#!/usr/bin/env python3
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# ── Load .env explicitly ──────────────────────────────────────
env_path = Path.home() / "dev_journal_scripts" / ".env"

# Read .env manually so we don't depend on dotenv at all
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
VAULT_PATH   = Path(os.getenv("VAULT_PATH"))

# Quick sanity check
if not AILY_API_KEY:
    print("❌ AILY_API_KEY not found in .env")
    sys.exit(1)

if not VAULT_PATH:
    print("❌ VAULT_PATH not found in .env")
    sys.exit(1)

# ── Read args passed by the hook ──────────────────────────────
# Called as: python3 log_push.py <repo_name> <branch> <commits>
if len(sys.argv) < 4:
    print("Usage: log_push.py <repo_name> <branch> <commits>")
    sys.exit(1)

repo_name   = sys.argv[1]
branch      = sys.argv[2]
commits_raw = sys.argv[3]   # newline-separated commit messages

# ── Build the prompt ──────────────────────────────────────────
prompt = f"""
I just pushed code to a repository. Write a short log entry for my work diary.

Repository: {repo_name}
Branch: {branch}
Commits:
{commits_raw}

Write a concise markdown log entry with:
- A one-line summary of what was done
- A bullet list of the commits, cleaned up (remove ticket numbers or noise)
- A "Notes" line if you can infer anything useful about the work

Keep it short. No intro text, just the markdown block ready to paste.
Use this exact format:

### [{datetime.now().strftime("%H:%M")}] {repo_name} — <one line summary>
- <commit 1>
- <commit 2>
**Notes:** <optional inference>
"""

# ── Call Aily gateway ─────────────────────────────────────────
headers = {
    "Authorization": f"Bearer {AILY_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": os.getenv("AILY_MODEL"),   
    "max_tokens": 500,
    "messages": [
        {"role": "user", "content": prompt}
    ]
}

try:
    response = requests.post(
        f"{AILY_GATEWAY}/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    log_entry = response.json()["choices"][0]["message"]["content"].strip()

except requests.exceptions.RequestException as e:
    print(f"⚠️  Aily gateway error: {e}")
    # Print the response body for debugging
    try:
        print(f"Response body: {e.response.text}")
    except:
        pass
    print("Falling back to raw log entry.")
    log_entry = f"""### [{datetime.now().strftime("%H:%M")}] {repo_name} — (raw log)
{commits_raw}
**Notes:** API unavailable at time of push.
"""

# ── Write to today's daily note ───────────────────────────────
today       = datetime.now().strftime("%Y-%m-%d")
daily_dir   = VAULT_PATH / "Daily"
daily_file  = daily_dir / f"{today}.md"

daily_dir.mkdir(parents=True, exist_ok=True)

# Create the file with a header if it doesn't exist yet
if not daily_file.exists():
    header = f"# Daily Log - {today}\n\n"
    daily_file.write_text(header)

# Append the new entry
with open(daily_file, "a") as f:
    f.write(f"\n{log_entry}\n")

print(f"✅ Logged to {daily_file}")