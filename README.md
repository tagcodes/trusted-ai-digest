# Trusted AI Digest

A weekly email with up to five **paste-once prompts** that upgrade how you use Claude Code, taken only from verified people at AI labs and official company pages. No reposts, no "an engineer at X said".

## How it works

```
registry feeds (RSS, YouTube channel IDs)
  -> collect last 7 days
  -> trust filter (registry author or official page; podcast hosts dropped)
  -> Groq extracts practices + who said them (re-checked against the registry)
  -> rank top 5, write install prompts (validated: skill path, explicit trigger, CLAUDE.md backup)
  -> draft emailed to owner -> owner clicks "Approve and send" -> testers
```

Runs entirely on free tiers: GitHub Actions, Groq, YouTube Data API (1 unit per channel, never search), Gmail SMTP.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m digest.main dry-run      # writes preview.html, sends nothing
```

Put keys in `.env` (git-ignored): `GROQ_API_KEY`, `YOUTUBE_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`.

## Weekly flow on GitHub

1. **Weekly draft** runs Monday 07:00 UTC, saves `drafts/DATE.html`, emails the owner.
2. Owner reads it. To approve: Actions -> **Approve and send** -> Run workflow.
3. Testers get it by BCC. Each draft can only be sent once.

Repository secrets: `GROQ_API_KEY`, `YOUTUBE_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `TESTER_EMAILS` (comma-separated), optional `OWNER_EMAIL`.

## Trust rules

See [SPEC.md](SPEC.md). Every decision is logged in [DECISIONS.md](DECISIONS.md); every dropped item and its reason is in `logs/`.
