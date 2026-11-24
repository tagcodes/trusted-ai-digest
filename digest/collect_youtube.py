"""YouTube collector: only channel IDs listed in the registry. Never uses search (100 units).

Cost per channel: 1 unit (playlistItems.list on the uploads playlist). Uploads playlist ID is
derived from the channel ID (UC... -> UU...), so no channels.list call is needed.
- A registry person's own channel -> source_type "person" (author = that person).
- A podcast / third-party channel -> source_type "podcast" (speaker checked per tip, host dropped).
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Item

API = "https://www.googleapis.com/youtube/v3/playlistItems"
UNITS_PER_CALL = 1


def _key():
    k = os.environ.get("YOUTUBE_API_KEY")
    if not k and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("YOUTUBE_API_KEY="):
                k = line.split("=", 1)[1].strip()
    return k


def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "trusted-ai-digest/0.1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def uploads_playlist(channel_id):
    if not channel_id.startswith("UC"):
        raise ValueError(f"not a channel ID: {channel_id!r}")
    return "UU" + channel_id[2:]


def _channels(registry):
    for p in registry.get("people", []):
        for cid in p.get("feeds", {}).get("youtube_channel_ids", []):
            yield cid, {"source_type": "person", "author": p["name"]}
    for pod in registry.get("podcasts", []):
        for cid in pod.get("youtube_channel_ids", []):
            yield cid, {"source_type": "podcast", "hosts": list(pod.get("hosts", []))}


def default_transcript(video_id):
    """Best effort. YouTube often blocks transcript fetches from cloud IPs; caller falls back."""
    from youtube_transcript_api import YouTubeTranscriptApi
    parts = YouTubeTranscriptApi().fetch(video_id)
    return " ".join(s.text for s in parts)


def collect(registry, days=7, now=None, get_json=_get_json, transcript=default_transcript,
            api_key=None):
    """Return (items, errors, units_used)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    key = api_key or _key()
    items, errors, units = [], [], 0
    chans = list(_channels(registry))
    if chans and not key:
        return [], [{"feed": "youtube", "error": "YOUTUBE_API_KEY not set; skipped"}], 0
    for cid, tmpl in chans:
        try:
            q = urllib.parse.urlencode({"part": "snippet", "maxResults": 15,
                                        "playlistId": uploads_playlist(cid), "key": key})
            units += UNITS_PER_CALL
            data = get_json(f"{API}?{q}")
        except Exception as e:
            errors.append({"feed": f"youtube:{cid}", "error": repr(e).replace(key or "#", "***")})
            continue
        for row in data.get("items", []):
            sn = row.get("snippet", {})
            vid = sn.get("resourceId", {}).get("videoId")
            try:
                d = datetime.fromisoformat(sn.get("publishedAt", "").replace("Z", "+00:00"))
            except ValueError:
                continue
            if not vid or d < cutoff or d > now + timedelta(days=1):
                continue
            text = ""
            try:
                text = transcript(vid)
            except Exception as e:
                errors.append({"feed": f"youtube:{vid}", "error": f"no transcript: {type(e).__name__}"})
            text = text or sn.get("description", "")
            items.append(Item(url=f"https://www.youtube.com/watch?v={vid}", title=sn.get("title", ""),
                              text=text, published=d.isoformat(), **tmpl))
    return items, errors, units
