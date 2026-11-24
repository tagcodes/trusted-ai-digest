"""Extract actionable practices from trusted items, re-check each tip's speaker, rank top 5."""
from .models import Item
from .trust import check

MAX_CHARS = 12000  # ~3K tokens; keeps each call under the free 8K TPM

EXTRACT_SYS = """You read one source (blog post, changelog, or podcast transcript) and pull out
concrete, actionable practices a programmer could adopt in their daily Claude Code workflow.
Rules:
- Only practices actually stated in the text. Never invent.
- speaker: the exact full name of the person who said/wrote the practice, as written in the text.
  For podcasts, attribute each tip to who said it; tips by the host must name the host.
  If the source is an official page with no named person, use "".
  If you cannot tell who said it, use "UNKNOWN".
- use_case: one line on when they use it.
- quote: a short verbatim excerpt (under 25 words) that supports the practice.
- Return an empty list if nothing is actionable for Claude Code users."""

EXTRACT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["practices"],
    "properties": {"practices": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["practice", "speaker", "use_case", "quote"],
        "properties": {k: {"type": "string"} for k in ["practice", "speaker", "use_case", "quote"]},
    }}},
}

RANK_SYS = """You pick the most useful practices for a programmer who uses Claude Code daily.
Prefer: concrete, habit-forming, broadly applicable. Reject near-duplicates (keep the best one).
Return the ids of at most 5 practices, best first."""

RANK_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["ids"],
    "properties": {"ids": {"type": "array", "items": {"type": "integer"}}},
}


def _source_text(item):
    return f"TITLE: {item.title}\nURL: {item.url}\n\n{(item.text or '')[:MAX_CHARS]}"


def extract(items, registry, llm):
    """Return (practices, dropped). Each practice dict has person/source attached."""
    practices, dropped = [], []
    for it in items:
        if not (it.text or "").strip():
            dropped.append({"url": it.url, "title": it.title, "reason": "no text to extract from"})
            continue
        try:
            out = llm.json(EXTRACT_SYS, _source_text(it), EXTRACT_SCHEMA, "practices")
        except Exception as e:
            dropped.append({"url": it.url, "title": it.title, "reason": f"extract failed: {e}"})
            continue
        for p in out.get("practices", []):
            d = check_practice(it, p, registry)
            if not d.keep:
                dropped.append({"url": it.url, "title": it.title, "practice": p["practice"], "reason": d.reason})
                continue
            practices.append({**p, "source_url": it.url, "source_title": it.title,
                              "source_type": it.source_type, "person": d.person})
    return practices, dropped


def check_practice(item, p, registry):
    """Trust rules applied per tip, using the speaker the LLM identified."""
    speaker = (p.get("speaker") or "").strip()
    if speaker.upper() == "UNKNOWN":
        speaker = ""
    if item.source_type == "official":
        if speaker:  # a named person on an official page must be in the registry to be credited
            named = check(Item(item.url, item.title, "person", author=speaker), registry)
            if named.keep:
                return named
        return check(item, registry)
    tip = Item(item.url, item.title, item.source_type, author=item.author, speaker=speaker or None,
               host=item.host, hosts=item.hosts, original_author=item.original_author)
    if item.source_type == "person" and speaker and item.author and \
            " ".join(speaker.lower().split()) != " ".join(item.author.lower().split()):
        # someone else quoted in a registry person's feed: credit only if they're in the registry
        tip.author = speaker
    return check(tip, registry)


def rank(practices, llm, k=5):
    if len(practices) <= 1:
        return practices[:k]
    listing = "\n".join(f"[{i}] {p['practice']} (use: {p['use_case']})" for i, p in enumerate(practices))
    out = llm.json(RANK_SYS, listing, RANK_SCHEMA, "ranking")
    seen, top = set(), []
    for i in out.get("ids", []):
        if isinstance(i, int) and 0 <= i < len(practices) and i not in seen:
            seen.add(i)
            top.append(practices[i])
        if len(top) == k:
            break
    return top
