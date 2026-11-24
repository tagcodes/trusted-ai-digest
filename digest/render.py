"""Email HTML: inline styles only (email clients strip <style>), single column, mobile-friendly."""
from html import escape

PASTE_LINE = "Paste once. Claude will do this automatically from now on:"


def byline(c):
    """'Name, Role, Company' with repeats removed (official pages: 'Anthropic, Official page')."""
    out = []
    for part in (c.get("name"), c.get("role"), c.get("company")):
        if part and part.strip().lower() not in {o.lower() for o in out}:
            out.append(part.strip())
    return ", ".join(out)


def card_html(c):
    return f"""
<tr><td style="padding:0 0 28px 0">
  <h2 style="margin:0 0 6px 0;font-size:19px;line-height:1.3;color:#111">{escape(c['title'])}</h2>
  <p style="margin:0 0 6px 0;font-size:15px;color:#111"><b>{escape(byline(c))}</b></p>
  <p style="margin:0 0 12px 0;font-size:15px;color:#444">When: {escape(c['when'])}</p>
  <p style="margin:0 0 6px 0;font-size:14px;color:#111">{PASTE_LINE}</p>
  <pre style="margin:0 0 10px 0;padding:12px;background:#f4f4f2;border:1px solid #ddd;border-radius:6px;font:13px/1.45 ui-monospace,Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;color:#111">{escape(c['install_prompt'])}</pre>
  <p style="margin:0;font-size:13px"><a href="{escape(c['source_url'], quote=True)}" style="color:#1a56db">Source: {escape(c['source_title'])}</a></p>
</td></tr>"""


def render(cards, date):
    body = "".join(card_html(c) for c in cards) or \
        '<tr><td style="font-size:15px;color:#444">No trusted, actionable tips this week.</td></tr>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trusted AI Digest {escape(date)}</title></head>
<body style="margin:0;padding:0;background:#ffffff">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;margin:0 auto;padding:20px 16px;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
<tr><td style="padding:0 0 20px 0">
  <h1 style="margin:0;font-size:22px;color:#111">Trusted AI Digest</h1>
  <p style="margin:4px 0 0 0;font-size:14px;color:#666">Week of {escape(date)} · {len(cards)} paste-once upgrades for Claude Code</p>
</td></tr>
{body}
<tr><td style="padding:12px 0 0 0;font-size:12px;color:#888;border-top:1px solid #eee">Every tip comes from a verified person at an AI lab or an official company page.</td></tr>
</table></body></html>"""
