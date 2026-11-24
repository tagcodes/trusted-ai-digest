"""CLI.
  collect   pull feeds, filter, log drops (no LLM)
  dry-run   full pipeline -> preview.html, sends nothing
  draft     full pipeline -> drafts/DATE.html, emails the owner only
  send      emails the latest approved draft to TESTER_EMAILS (BCC)
"""
import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .cards import write_card
from . import collect_youtube
from .collect_rss import collect as collect_rss, page_text
from .extract import extract, rank
from .render import render
from .trust import filter_items, load_registry


def collect(reg, days=7):
    """RSS + YouTube. YouTube quota units are reported as a pseudo-error line for the log."""
    items, errors = collect_rss(reg, days=days)
    yt, yerr, units = collect_youtube.collect(reg, days=days)
    errors += yerr
    if units:
        errors.append({"feed": "youtube", "error": f"info: {units} quota units used (limit 10000/day)"})
    return items + yt, errors


def cmd_collect(args):
    reg = load_registry(args.registry)
    items, errors = collect(reg, days=args.days)
    kept, dropped = filter_items(items, reg)

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    Path("logs").mkdir(exist_ok=True)
    log = {
        "date": day,
        "feed_errors": errors,
        "dropped": [{"url": i.url, "title": i.title, "reason": d.reason} for i, d in dropped],
    }
    Path(f"logs/dropped-{day}.json").write_text(json.dumps(log, indent=2))
    Path(f"logs/kept-{day}.json").write_text(
        json.dumps([{**asdict(i), "reason": d.reason} for i, d in kept], indent=2)
    )

    print(f"collected {len(items)}  kept {len(kept)}  dropped {len(dropped)}  feed errors {len(errors)}")
    for i, d in kept:
        print(f"  KEEP  {i.published[:10]}  {i.title[:70]}  [{d.reason}]")
    for i, d in dropped:
        print(f"  DROP  {i.published[:10]}  {i.title[:70]}  [{d.reason}]")
    for e in errors:
        print(f"  ERR   {e['feed']}: {e['error']}")


def run_pipeline(reg, llm, days=7, collect_fn=None, text_fn=page_text, log=print):
    """Collect -> filter -> extract (+per-tip trust) -> rank -> cards. Returns (cards, report)."""
    items, errors = (collect_fn or collect)(reg, days=days)
    podcasts = [i for i in items if i.source_type == "podcast"]  # speaker checked per tip
    kept, dropped = filter_items([i for i in items if i.source_type != "podcast"], reg)
    dropped_log = [{"url": i.url, "title": i.title, "reason": d.reason} for i, d in dropped]
    todo = [i for i, _ in kept] + podcasts
    for it in todo:
        if not (it.text or "").strip():
            try:
                it.text = text_fn(it.url)
            except Exception as e:
                errors.append({"feed": it.url, "error": f"page fetch: {e!r}"})
    log(f"collected {len(items)}, extracting from {len(todo)}")
    practices, d2 = extract(todo, reg, llm)
    dropped_log += d2
    log(f"{len(practices)} trusted practices; ranking")
    cards = []
    for p in rank(practices, llm):
        c, why = write_card(p, llm)
        if c:
            cards.append(c)
        else:
            dropped_log.append({"url": p["source_url"], "practice": p["practice"], "reason": why})
    return cards, {"feed_errors": errors, "dropped": dropped_log, "practices": len(practices)}


def _build(args):
    from .llm import Groq
    reg = load_registry(args.registry)
    cards, report = run_pipeline(reg, Groq(), days=args.days)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    Path("logs").mkdir(exist_ok=True)
    Path(f"logs/run-{day}.json").write_text(json.dumps({**report, "cards": cards}, indent=2))
    return cards, report, day


def cmd_dry_run(args):
    cards, report, day = _build(args)
    Path(args.out).write_text(render(cards, day))
    print(f"{len(cards)} cards -> {args.out}; {len(report['dropped'])} dropped (logs/run-{day}.json)")


def subject(day):
    return f"Trusted AI Digest, week of {day}"


def cmd_draft(args):
    from .send import env, send
    cards, report, day = _build(args)
    Path("drafts").mkdir(exist_ok=True)
    out = Path(f"drafts/{day}.html")
    out.write_text(render(cards, day))
    print(f"{len(cards)} cards -> {out}")
    if args.no_email:
        return
    owner = env("OWNER_EMAIL") if _has("OWNER_EMAIL") else env("GMAIL_ADDRESS")
    send(out.read_text(), "[DRAFT] " + subject(day), [owner])
    print("draft emailed to owner")


def _has(name):
    import os
    return bool(os.environ.get(name))


def latest_draft(folder="drafts"):
    files = sorted(Path(folder).glob("????-??-??.html"))
    if not files:
        raise SystemExit("no drafts/ found; run `draft` first")
    return files[-1]


def cmd_send(args):
    from .send import env, parse_emails, send
    d = Path(args.draft) if args.draft else latest_draft()
    sent_log = Path("drafts/sent.json")
    sent = json.loads(sent_log.read_text()) if sent_log.exists() else []
    if d.name in sent and not args.force:
        raise SystemExit(f"{d.name} was already sent; use --force to resend")
    testers = parse_emails(env("TESTER_EMAILS"))
    sender = env("GMAIL_ADDRESS")
    send(d.read_text(), subject(d.stem), [sender], bcc=testers)
    sent_log.write_text(json.dumps(sent + [d.name], indent=2))
    print(f"sent {d.name} to {len(testers)} testers (BCC)")


def main():
    ap = argparse.ArgumentParser(prog="digest")
    ap.add_argument("--registry", default="registry.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--days", type=int, default=7)
    c.set_defaults(func=cmd_collect)
    d = sub.add_parser("dry-run", help="full pipeline, write email HTML locally, send nothing")
    d.add_argument("--days", type=int, default=7)
    d.add_argument("--out", default="preview.html")
    d.set_defaults(func=cmd_dry_run)
    r = sub.add_parser("draft", help="full pipeline, save drafts/DATE.html, email owner only")
    r.add_argument("--days", type=int, default=7)
    r.add_argument("--no-email", action="store_true")
    r.set_defaults(func=cmd_draft)
    s = sub.add_parser("send", help="email latest (or given) draft to TESTER_EMAILS")
    s.add_argument("--draft")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_send)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
