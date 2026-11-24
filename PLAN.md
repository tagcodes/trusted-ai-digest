# PLAN.md – Trusted AI Digest (MVP)

Status (2026-11-24): slices 1–6 built and tested locally. Slice 7 (grow + verify registry) is owner work.

## Layout

```
registry.json            trusted people + official sources
digest/
  models.py              Item, Practice, Card dataclasses
  trust.py               trust filter (rules 1–4), returns keep/drop + reason
  collect_rss.py         RSS/Atom, last 7 days
  collect_youtube.py     registry channel IDs only (no search) + transcripts
  extract.py             Groq: item -> practices (speaker, role, use case)
  rank.py                top 5, dedupe
  cards.py               Groq: practice -> paste-once install prompt
  render.py              email HTML (mobile, copyable <pre> boxes)
  send.py                Gmail SMTP (app password)
  main.py                CLI: --dry-run | --draft | --send <draft>
tests/                   pytest + fixtures
drafts/YYYY-MM-DD.html   saved drafts (committed by the Action)
logs/dropped-YYYY-MM-DD.json   every dropped item + reason
.github/workflows/       weekly.yml, send.yml
DECISIONS.md
```

## Slices (each ends with a check)

1. **Registry + trust filter.** 5 candidate entries I draft (Claude Code team / Anthropic staff) + official Anthropic pages; you confirm two proofs each. Tests: registry author passes, unknown reposter fails, podcast host quote fails, reshare traced to registry original passes, official page passes. ✔ `pytest` green.
2. **RSS collector.** Anthropic engineering blog, Claude Code changelog, help centre, Latent Space. ✔ Prints last-7-day items; dropped items logged.
3. **Extract + cards (Groq).** Check current Groq models/limits first and record choice. Prompt enforces: skill in `~/.claude/skills` with explicit trigger description + backup line in `~/.claude/CLAUDE.md`. ✔ `--dry-run` writes `preview.html`; you paste one prompt into fresh Claude Code to test.
4. **YouTube collector.** Data API `playlistItems` on channel uploads (1 unit/call), transcripts; guest-only rule. ✔ Quota use logged, well under 10,000.
5. **Email (Gmail SMTP) to owner + approval.** `--draft` emails you and saves `drafts/`. `send.yml` (manual "Run workflow" button) sends the latest draft to testers. ✔ Draft arrives on your phone.
6. **GitHub Actions cron.** Monday 07:00 UTC runs `--draft`. Secrets: `GROQ_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `YOUTUBE_API_KEY`, `TESTER_EMAILS`. ✔ Manual trigger run succeeds.
7. **Grow registry to 20–30**, each with two proofs and last-verified date.

## Blocker to resolve before slice 5 sends to testers

RESOLVED 2026-11-20: send via Gmail SMTP with an app password for the first 3 test weeks (free, no domain). Revisit domain + Resend after week 3.

## Out of scope

X API, signup site, accounts, personalisation, plugin, tier 3.
