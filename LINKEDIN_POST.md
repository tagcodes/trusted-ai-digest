# LinkedIn post (draft)

I kept saving "how I use AI" posts and videos… and never watching them. My Claude Code setup was going stale.

So I built a small fix: **Trusted AI Digest**, a weekly email with up to 5 tips, each one a prompt you paste into Claude Code *once*. Claude saves it as a skill or rule, and does it automatically from then on.

The part I cared about most: **trust.** Feeds are full of "this is from an engineer at an AI lab" reposts nobody can verify. So the digest only uses:
✅ people in a hand-checked registry (each verified with 2+ independent proofs)
✅ official company pages: docs, engineering blogs, changelogs
❌ reposts are traced to the original, or dropped
❌ podcast tips count only if the verified guest said them, never the host

Every dropped item is logged with the reason.

How it runs, for $0:
• GitHub Actions builds a draft every Monday
• Groq (free tier) pulls out the practices and writes the install prompts
• Code checks each prompt really saves a permanent habit with a clear trigger
• I approve the draft, then it goes to testers

I'm testing it with 3 friends for the next 3 weeks. The metric I'm watching isn't opens. It's how many prompts people actually paste, and whether the habit still triggers a week later.

Built with Claude Code, one slice at a time, tests first.

Code: https://github.com/tagcodes/trusted-ai-digest

What's one Claude Code habit you'd want on autopilot?

#ClaudeCode #AI #DeveloperTools #BuildInPublic
