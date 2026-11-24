"""Trust filter: SPEC.md trust rules 1-4. Anything not provably trusted is dropped."""
import json
from pathlib import Path
from urllib.parse import urlparse

from .models import Decision, Item

MIN_PROOFS = 2
MVP_TIERS = {1, 2}  # tier 3 is out of scope for MVP


def load_registry(path="registry.json"):
    return json.loads(Path(path).read_text())


def _norm(name):
    return " ".join((name or "").lower().split())


def find_person(registry, name):
    """Return a verified, in-scope registry person matching name, else None."""
    if not name:
        return None
    n = _norm(name)
    for p in registry.get("people", []):
        names = [_norm(p["name"])] + [_norm(a) for a in p.get("aliases", [])]
        if n in names:
            if len(p.get("verified_by", [])) < MIN_PROOFS:
                return None
            if p.get("tier") not in MVP_TIERS:
                return None
            return p
    return None


def is_official(registry, url):
    u = urlparse(url)
    host = (u.hostname or "").lower()
    full = host + u.path
    for src in registry.get("official_sources", []):
        for d in src["domains"]:
            d = d.lower()
            if "/" in d:
                if full == d or full.startswith(d.rstrip("/") + "/"):
                    return True
            elif host == d or host.endswith("." + d):
                return True
    return False


def check(item: Item, registry) -> Decision:
    t = item.source_type

    if t == "official":
        if is_official(registry, item.url):
            return Decision(True, "official company page")
        return Decision(False, "claims official but URL is not an official domain")

    if t == "reshare":
        p = find_person(registry, item.original_author)
        if p:
            return Decision(True, f"reshare traced to registry author {p['name']}", p)
        return Decision(False, f"reshare; original author {item.original_author!r} not in registry")

    if t == "podcast":
        if not item.speaker:
            return Decision(False, "podcast tip with no identified speaker")
        hosts = {_norm(h) for h in (item.hosts or [item.host]) if h}
        if _norm(item.speaker) in hosts:
            return Decision(False, f"tip said by host {item.speaker!r}, not a verified guest")
        p = find_person(registry, item.speaker)
        if p:
            return Decision(True, f"verified guest {p['name']}", p)
        return Decision(False, f"speaker {item.speaker!r} not in registry")

    if t == "person":
        p = find_person(registry, item.speaker or item.author)
        if p:
            return Decision(True, f"registry author {p['name']}", p)
        return Decision(False, f"author {item.author!r} not in registry")

    return Decision(False, f"unknown source_type {t!r}")


def filter_items(items, registry):
    kept, dropped = [], []
    for it in items:
        d = check(it, registry)
        (kept if d.keep else dropped).append((it, d))
    return kept, dropped
