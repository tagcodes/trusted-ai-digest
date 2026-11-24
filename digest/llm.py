"""Minimal Groq client (OpenAI-compatible REST) with strict JSON schema output."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
# Free tier: 8K tokens/minute. Space calls so a ~4K-token request never trips it.
MIN_GAP_S = float(os.environ.get("GROQ_MIN_GAP_S", "35"))
_last = [0.0]


def _key():
    k = os.environ.get("GROQ_API_KEY")
    if not k and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                k = line.split("=", 1)[1].strip()
    if not k:
        raise RuntimeError("GROQ_API_KEY not set (env var or .env file)")
    return k


class Groq:
    def __init__(self, model=MODEL):
        self.model = model

    def json(self, system, user, schema, name="out", retries=3):
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": name, "strict": True, "schema": schema}},
            "temperature": 0.2,
        }
        for attempt in range(retries):
            wait = MIN_GAP_S - (time.time() - _last[0])
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={
                "Authorization": f"Bearer {_key()}", "Content-Type": "application/json",
                "User-Agent": "trusted-ai-digest/0.1"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    _last[0] = time.time()
                    data = json.loads(r.read())
                return json.loads(data["choices"][0]["message"]["content"])
            except urllib.error.HTTPError as e:
                _last[0] = time.time()
                if e.code == 429 and attempt < retries - 1:
                    time.sleep(float(e.headers.get("retry-after", "60")))
                    continue
                raise RuntimeError(f"Groq HTTP {e.code}: {e.read()[:300]!r}") from e
