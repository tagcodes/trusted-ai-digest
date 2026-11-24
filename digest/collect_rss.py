"""RSS / listing collector: items from registry feeds published in the last N days."""
import html
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import feedparser

from .models import Item

UA = "trusted-ai-digest/0.1"
TIMEOUT = 20


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "replace")


def _entry_date(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def _strip(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def parse_rss(text):
    """Return [(url, title, date, author, body)] from RSS/Atom text."""
    out = []
    for e in feedparser.parse(text).entries:
        body = ""
        if e.get("content"):
            body = e.content[0].get("value", "")
        body = _strip(body or e.get("summary", ""))
        out.append((e.get("link", ""), e.get("title", ""), _entry_date(e), e.get("author"), body))
    return out


# anthropic.com has no RSS; listing pages embed JSON with href/title/date.
_LISTING_RE = re.compile(
    r'\\"href\\":\\"(?P<href>[^\\"]+)\\",\\"title\\":\\"(?P<title>[^\\"]+)\\"'
    r'(?:,\\"[a-zA-Z]+\\":(?:\\"[^\\"]*\\"|[^,}]+))*?,\\"date\\":\\"(?P<date>[^\\"]+)\\"'
)


def parse_anthropic_listing(text, base_url):
    seen, out = set(), []
    for m in _LISTING_RE.finditer(text):
        url = urljoin(base_url, m["href"])
        if url in seen:
            continue
        seen.add(url)
        try:
            d = datetime.strptime(m["date"], "%b %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            d = None
        out.append((url, html.unescape(m["title"]), d, None, ""))
    return out


PARSERS = {
    "rss": lambda text, url: parse_rss(text),
    "anthropic_listing": parse_anthropic_listing,
}


def _feeds(registry):
    """Yield (feed, item template kwargs) for every registry feed."""
    for src in registry.get("official_sources", []):
        for f in src.get("feeds", []):
            yield f, {"source_type": "official"}
    for p in registry.get("people", []):
        for f in p.get("feeds", {}).get("rss", []):
            yield f, {"source_type": "person", "author": p["name"]}
    for pod in registry.get("podcasts", []):
        for f in pod.get("feeds", []):
            yield f, {"source_type": "podcast", "hosts": list(pod.get("hosts", []))}


def collect(registry, days=7, now=None, fetch=_fetch):
    """Return (items, errors). Undated items are skipped (can't prove they're recent)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    items, errors = [], []
    for feed, tmpl in _feeds(registry):
        try:
            text = fetch(feed["url"])
            rows = PARSERS[feed["type"]](text, feed["url"])
        except Exception as e:  # one bad feed must not kill the run
            errors.append({"feed": feed["url"], "error": repr(e)})
            continue
        if not rows:
            errors.append({"feed": feed["url"], "error": "parsed 0 entries (layout changed?)"})
        for url, title, date, author, body in rows:
            if not date or date < cutoff or date > now + timedelta(days=1):
                continue
            kw = dict(tmpl)
            if tmpl["source_type"] == "official":
                kw["author"] = author
            items.append(Item(url=url, title=title, text=body, published=date.isoformat(), **kw))
    return items, errors


def page_text(url, fetch=_fetch):
    """Fetch an article page and return readable text (scripts/styles/nav stripped)."""
    s = fetch(url)
    s = re.sub(r"(?is)<(script|style|nav|header|footer|svg|noscript)\b.*?</\1>", " ", s)
    m = re.search(r"(?is)<(article|main)\b.*?</\1>", s)
    s = _strip(m.group(0) if m else s)
    return re.sub(r"\s+", " ", s).strip()
