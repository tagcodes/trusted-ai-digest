# SPEC.md – Trusted AI Digest (MVP)

A weekly email that gives programmers five paste-once prompts that upgrade how they use Claude Code, taken only from verified people at AI labs and official company pages.

## How to use this file in Claude Code

1. Save this as SPEC.md in an empty project folder.
2. Start a fresh Claude Code session and say: "Read SPEC.md. Interview me about anything unclear, then write a plan. Do not write code until I approve the plan."
3. Build in the order in "Build order", one slice at a time. After each slice, verify it works before moving on.
4. Keep a DECISIONS.md: one line per product or technical decision and why.

## Problem

Programmers save "how I use AI" posts and videos but never watch them, so their Claude Code workflow goes stale. Existing roundups say what changed; nobody tells them exactly what to do. Social feeds are noisy and full of reposts with unverifiable claims like "this is from an Anthropic engineer".

## Target user

Programmers who use Claude Code daily. MVP testers: three friends.

## Definition of done (MVP)

- Every Monday, a digest of up to five cards is generated automatically.
- Every card passes the trust rules below.
- The owner reviews and approves the draft before it is sent.
- The approved digest arrives in the testers' inboxes, readable on mobile, with prompts easy to copy.
- Total running cost is $0.

## Trust rules (non-negotiable)

1. Content is kept only if its author is in the trusted registry, or it is an official company page (docs, help centre, engineering blog, changelog).
2. If the exact speaker cannot be identified as a registry person, the content is noise and is dropped.
3. Reshares are traced to the original; keep only if the original author is in the registry.
4. Podcasts and third-party YouTube channels: keep only tips said by the verified guest, never the host.
5. Every card shows the person's name and role in bold, the case they use it for, and a link to the exact source.

## Trusted registry

A hand-curated file, `registry.json`, with 20–30 entries for the MVP. Each entry: name, role, company, tier, verified-by (at least two independent proofs such as LinkedIn, company blog byline, conference speaker page), source feeds (RSS, YouTube channel ID), last-verified date.

Tiers: 1 = builds the tool (for example the Claude Code team); 2 = other AI lab employees; 3 = vetted outside practitioners (later, not MVP). Official company pages are trusted sources without a named person. Re-verify every entry every three months.

## Sources (MVP)

- RSS: official engineering blogs, docs changelogs, help-centre tips, podcasts such as Latent Space.
- YouTube Data API: only the channel IDs in the registry; never use search (one search costs 100 of the 10,000 free daily units).
- X: out of scope for automation (paid API). The owner skims an X List manually and can paste links in.

## Pipeline

1. Collect: pull items published in the last 7 days from registry feeds.
2. Filter: apply the trust rules; log every dropped item with the reason.
3. Extract: an LLM reads each item (transcript or text) and pulls out actionable practices, each with speaker, role and use case.
4. Rank: pick the top five practices by usefulness to a Claude Code programmer; no duplicates.
5. Write cards: turn each practice into a paste-once install prompt (see Card format).
6. Draft: build the email and send it to the owner only.
7. Approve: owner approves; then send to the tester list.

## Card format

Each card has: a short title; **Name, Role, Company** in bold; when they use it (one line); the line "Paste once. Claude will do this automatically from now on:"; the install prompt in a copyable box; the source link.

Install prompts must make the habit permanent, never one-off: they save it as a skill in `~/.claude/skills`, a slash command, or a rule in the personal `~/.claude/CLAUDE.md`. A skill's description must state when to trigger, for example "Use automatically after any feature is added or changed", and the prompt also adds a backup trigger line to CLAUDE.md. (Lesson from testing: a skill with a vague description did not trigger.)

## Tech stack (all free tier)

- Scheduler: GitHub Actions cron, weekly (public repo, or private within 2,000 free minutes).
- LLM: Groq free tier; check current available models and daily limits before choosing.
- Email: Resend free plan (3,000 emails a month, 100 a day).
- Language and storage: owner to decide in the interview; keep it simple (JSON files in the repo are fine).
- Secrets: API keys only in GitHub Actions secrets, never committed.

## Out of scope for MVP

X API, a sign-up website, user accounts, personalisation, the in-Claude-Code plugin (version two), tier-3 outside practitioners.

## Verification

- Unit-test the trust filter with fixtures: a registry author passes, an unknown reposter fails, a podcast host quote fails.
- Dry-run mode: run the full pipeline and write the email to a local HTML file instead of sending.
- Before shipping, the owner pastes each install prompt into a fresh Claude Code session and confirms it saves the habit and triggers in a new session.

## Success metrics

- Primary: install rate, the share of cards each tester actually pastes.
- Stickiness: did the habit still trigger a week later.
- Trust: zero cards that fail the trust rules.
- Retention: testers open three digests in a row.

## Build order

1. `registry.json` with 5 entries + the trust filter + its tests.
2. RSS collector for official blogs and changelogs.
3. Extract and card writing with Groq; output to a local HTML preview.
4. YouTube channel collector.
5. Resend email to owner only, then the approval step.
6. GitHub Actions weekly schedule.
7. Grow the registry to 20–30 entries.
