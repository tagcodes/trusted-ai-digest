import json
from pathlib import Path

from digest import main as M
from digest.render import byline
from digest.send import build, parse_emails, send


class FakeSMTP:
    sent = []
    def __init__(self, host, port): self.host = host
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def login(self, u, p): self.user = u
    def send_message(self, msg, to_addrs): FakeSMTP.sent.append((msg, to_addrs))


def test_parse_emails():
    assert parse_emails("a@x.com, b@x.com;c@x.com\n") == ["a@x.com", "b@x.com", "c@x.com"]


def test_testers_are_bcc_not_visible(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pw")
    FakeSMTP.sent = []
    send("<p>hi</p>", "S", ["me@gmail.com"], bcc=["a@x.com", "b@x.com"], smtp=FakeSMTP)
    msg, to = FakeSMTP.sent[0]
    assert set(to) == {"me@gmail.com", "a@x.com", "b@x.com"}
    assert "a@x.com" not in msg.as_string()


def test_byline_dedupes_official():
    assert byline({"name": "Anthropic", "role": "Official page", "company": "Anthropic"}) == \
        "Anthropic, Official page"
    assert byline({"name": "Ada", "role": "Eng", "company": "Lab"}) == "Ada, Eng, Lab"


def test_send_refuses_resend(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GMAIL_ADDRESS", "me@gmail.com")
    monkeypatch.setenv("TESTER_EMAILS", "a@x.com")
    Path("drafts").mkdir()
    Path("drafts/2026-11-23.html").write_text("<p>x</p>")
    calls = []
    monkeypatch.setattr("digest.send.send", lambda *a, **k: calls.append((a, k)))

    class A: draft = None; force = False
    M.cmd_send(A)
    assert calls and calls[0][1]["bcc"] == ["a@x.com"]
    assert json.loads(Path("drafts/sent.json").read_text()) == ["2026-11-23.html"]
    try:
        M.cmd_send(A)
        assert False, "should refuse to resend"
    except SystemExit as e:
        assert "already sent" in str(e)
