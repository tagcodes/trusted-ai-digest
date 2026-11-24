from datetime import datetime, timezone

from digest.collect_rss import collect, parse_anthropic_listing
from digest.trust import filter_items

NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>v2.1.0</title><link href="https://github.com/anthropics/claude-code/releases/tag/v2.1.0"/>
<updated>2026-11-18T10:00:00Z</updated><content type="html">&lt;p&gt;New /foo&lt;/p&gt;</content></entry>
<entry><title>old</title><link href="https://github.com/anthropics/claude-code/releases/tag/v1"/>
<updated>2026-10-01T10:00:00Z</updated></entry>
<entry><title>undated</title><link href="https://github.com/anthropics/claude-code/releases/tag/v0"/></entry>
</feed>"""

POD = """<?xml version="1.0"?><rss version="2.0"><channel><item><title>Ep 1</title>
<link>https://www.latent.space/p/ep1</link><pubDate>Wed, 18 Nov 2026 10:00:00 GMT</pubDate>
<description>chat</description></item></channel></rss>"""

LISTING = (r'x\"href\":\"/engineering/a\",\"title\":\"Post A\",\"span\":3,\"date\":\"Nov 17, 2026\"'
           r'y\"href\":\"/engineering/a\",\"title\":\"Post A\",\"date\":\"Nov 17, 2026\"'
           r'z\"href\":\"/engineering/b\",\"title\":\"Old B\",\"date\":\"Jan 2, 2026\"')

REG = {
    "official_sources": [
        {"name": "Blog", "domains": ["anthropic.com"],
         "feeds": [{"type": "anthropic_listing", "url": "https://www.anthropic.com/engineering"}]},
        {"name": "CL", "domains": ["github.com/anthropics/claude-code"],
         "feeds": [{"type": "rss", "url": "https://gh/atom"}]},
    ],
    "people": [],
    "podcasts": [{"name": "LS", "hosts": ["swyx"], "feeds": [{"type": "rss", "url": "https://pod"}]}],
}

PAGES = {"https://www.anthropic.com/engineering": LISTING, "https://gh/atom": ATOM, "https://pod": POD}


def fake_fetch(url):
    return PAGES[url]


def test_listing_parses_and_dedupes():
    rows = parse_anthropic_listing(LISTING, "https://www.anthropic.com/engineering")
    assert [r[0] for r in rows] == ["https://www.anthropic.com/engineering/a", "https://www.anthropic.com/engineering/b"]


def test_collect_last_7_days_only():
    items, errors = collect(REG, now=NOW, fetch=fake_fetch)
    titles = {i.title for i in items}
    assert titles == {"Post A", "v2.1.0", "Ep 1"}
    assert errors == []


def test_collected_items_through_trust_filter():
    items, _ = collect(REG, now=NOW, fetch=fake_fetch)
    kept, dropped = filter_items(items, REG)
    assert {i.title for i, _ in kept} == {"Post A", "v2.1.0"}
    # podcast has no identified speaker yet (slice 3 extracts it) -> dropped with a reason
    assert [i.title for i, _ in dropped] == ["Ep 1"]
    assert "no identified speaker" in dropped[0][1].reason


def test_bad_feed_is_logged_not_fatal():
    def flaky(url):
        if url == "https://pod":
            raise OSError("boom")
        return PAGES[url]
    items, errors = collect(REG, now=NOW, fetch=flaky)
    assert len(items) == 2 and errors[0]["feed"] == "https://pod"


def test_empty_parse_is_flagged():
    items, errors = collect(REG, now=NOW, fetch=lambda u: "nothing" if "anthropic" in u else PAGES[u])
    assert any("0 entries" in e["error"] for e in errors)
