from datetime import datetime, timezone

import pytest

from digest.collect_youtube import collect, uploads_playlist
from digest.trust import check

NOW = datetime(2026, 11, 24, tzinfo=timezone.utc)
REG = {
    "people": [{"name": "Ada Builder", "role": "Eng", "company": "Lab", "tier": 1,
                "verified_by": ["a", "b"], "feeds": {"youtube_channel_ids": ["UCada"]}}],
    "podcasts": [{"name": "Pod", "hosts": ["Hal Host"], "youtube_channel_ids": ["UCpod"]}],
}


def fake_api(urls):
    def get(url):
        urls.append(url)
        assert "search" not in url  # never the 100-unit search endpoint
        return {"items": [
            {"snippet": {"title": "new", "publishedAt": "2026-11-22T10:00:00Z",
                         "resourceId": {"videoId": "v1"}, "description": "desc"}},
            {"snippet": {"title": "old", "publishedAt": "2026-10-01T10:00:00Z",
                         "resourceId": {"videoId": "v0"}}},
        ]}
    return get


def test_uploads_playlist():
    assert uploads_playlist("UCabc") == "UUabc"
    with pytest.raises(ValueError):
        uploads_playlist("PLxyz")


def test_collect_recent_only_and_units():
    urls = []
    items, errors, units = collect(REG, now=NOW, get_json=fake_api(urls),
                                   transcript=lambda v: "spoken words", api_key="k")
    assert [i.title for i in items] == ["new", "new"]
    assert units == 2 and len(urls) == 2
    assert items[0].source_type == "person" and items[0].author == "Ada Builder"
    assert items[1].source_type == "podcast" and items[1].hosts == ["Hal Host"]
    assert items[0].text == "spoken words"


def test_transcript_failure_falls_back_to_description():
    def boom(v):
        raise RuntimeError("blocked")
    items, errors, _ = collect(REG, now=NOW, get_json=fake_api([]), transcript=boom, api_key="k")
    assert items[0].text == "desc"
    assert any("no transcript" in e["error"] for e in errors)


def test_no_key_skips_cleanly(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.chdir("/tmp")
    items, errors, units = collect(REG, now=NOW, get_json=fake_api([]))
    assert items == [] and units == 0 and "not set" in errors[0]["error"]


def test_own_channel_passes_trust():
    items, _, _ = collect(REG, now=NOW, get_json=fake_api([]), transcript=lambda v: "x", api_key="k")
    assert check(items[0], REG).keep
