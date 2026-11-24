from dataclasses import dataclass, field
from typing import Optional

# source_type values:
#   "official"     - official company page (docs, blog, changelog)
#   "person"       - a registry person's own feed/post
#   "reshare"      - someone reposting; original_author must be set
#   "podcast"      - podcast or third-party YouTube; speaker + host must be set


@dataclass
class Item:
    url: str
    title: str
    source_type: str
    author: Optional[str] = None
    speaker: Optional[str] = None
    host: Optional[str] = None
    hosts: list = field(default_factory=list)
    original_author: Optional[str] = None
    text: str = ""
    published: Optional[str] = None


@dataclass
class Decision:
    keep: bool
    reason: str
    person: Optional[dict] = None  # registry entry when kept via a person
