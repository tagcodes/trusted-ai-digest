"""Email via Gmail SMTP with an app password (free; no domain needed). See DECISIONS.md."""
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 465


def env(name):
    v = os.environ.get(name)
    if not v and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith(name + "="):
                v = line.split("=", 1)[1].strip()
    if not v:
        raise RuntimeError(f"{name} not set (env var / GitHub secret / .env)")
    return v


def parse_emails(s):
    return [e.strip() for e in s.replace(";", ",").replace("\n", ",").split(",") if e.strip()]


def build(html, subject, sender, to, bcc=()):
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = subject, sender, ", ".join(to)
    m.set_content("This digest is HTML. Open it in a mail app that shows HTML.")
    m.add_alternative(html, subtype="html")
    return m


def send(html, subject, to, bcc=(), smtp=smtplib.SMTP_SSL):
    sender = env("GMAIL_ADDRESS")
    msg = build(html, subject, sender, to, bcc)
    with smtp(SMTP_HOST, SMTP_PORT) as s:
        s.login(sender, env("GMAIL_APP_PASSWORD"))
        s.send_message(msg, to_addrs=list(to) + list(bcc))
    return sender
