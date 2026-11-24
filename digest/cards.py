"""Turn a practice into a card with a paste-once install prompt that makes the habit permanent."""
import re

CARD_SYS = """You write one card for a weekly digest for Claude Code users.
Write an INSTALL PROMPT the reader pastes into Claude Code once. Claude must then make the habit
permanent, never one-off. Choose exactly one mechanism:
- "skill": create ~/.claude/skills/<kebab-name>/SKILL.md with YAML frontmatter `name` and
  `description`. The description MUST start with "Use automatically when" or
  "Use automatically after" and name a concrete trigger. The prompt MUST ALSO append a backup
  trigger line to ~/.claude/CLAUDE.md, e.g. "- After <trigger>, use the <name> skill."
- "command": create ~/.claude/commands/<name>.md (a slash command) with the steps.
- "rule": append a rule to the personal ~/.claude/CLAUDE.md.
The install prompt must be self-contained, give the exact file path and the full file content
to write, and end by asking Claude to confirm the file was saved.
Do not invent capabilities that the practice does not describe.
title: under 8 words. when: one line, when the person uses it."""

CARD_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["title", "when", "mechanism", "install_prompt"],
    "properties": {
        "title": {"type": "string"}, "when": {"type": "string"},
        "mechanism": {"type": "string", "enum": ["skill", "command", "rule"]},
        "install_prompt": {"type": "string"},
    },
}


def validate_prompt(card):
    """Return a list of problems; empty means the prompt meets SPEC.md card rules."""
    p, m, errs = card["install_prompt"], card["mechanism"], []
    if m == "skill":
        if not re.search(r"~/\.claude/skills/", p):
            errs.append("skill prompt does not save to ~/.claude/skills/")
        if not re.search(r"Use automatically (when|after)", p, re.I):
            errs.append("skill description lacks an explicit 'Use automatically when/after' trigger")
        if "~/.claude/CLAUDE.md" not in p:
            errs.append("skill prompt lacks backup trigger line in ~/.claude/CLAUDE.md")
    elif m == "command":
        if "~/.claude/commands/" not in p:
            errs.append("command prompt does not save to ~/.claude/commands/")
    elif m == "rule":
        if "~/.claude/CLAUDE.md" not in p:
            errs.append("rule prompt does not write to ~/.claude/CLAUDE.md")
    return errs


def byline(practice):
    p = practice.get("person")
    if p:
        return p["name"], p["role"], p["company"]
    return "Anthropic", "Official page", "Anthropic"


def write_card(practice, llm, retries=2):
    """Return (card, None) or (None, reason)."""
    user = (f"PRACTICE: {practice['practice']}\nUSE CASE: {practice['use_case']}\n"
            f"SUPPORTING QUOTE: {practice['quote']}\nSOURCE: {practice['source_url']}")
    errs = []
    for _ in range(retries):
        msg = user if not errs else user + "\n\nYour previous attempt failed these checks; fix them:\n- " + "\n- ".join(errs)
        try:
            c = llm.json(CARD_SYS, msg, CARD_SCHEMA, "card")
        except Exception as e:
            return None, f"card failed: {e}"
        errs = validate_prompt(c)
        if not errs:
            name, role, company = byline(practice)
            return {**c, "name": name, "role": role, "company": company,
                    "source_url": practice["source_url"], "source_title": practice["source_title"]}, None
    return None, "install prompt failed checks: " + "; ".join(errs)
