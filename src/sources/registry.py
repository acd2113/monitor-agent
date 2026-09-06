import json
from dataclasses import dataclass, field
from pathlib import Path

from src.config import BASE_DIR


@dataclass
class SourceConfig:
    name: str
    kind: str
    url: str = ""
    feed_url: str = ""
    keywords: list[str] = field(default_factory=list)


def load_sources(path):
    if not path:
        return []

    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = BASE_DIR / path
    if not file_path.exists():
        return []

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    sources = []
    for row in data:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind", "")).strip().lower()
        url = str(row.get("url") or row.get("feed_url") or "")
        feed_url = str(row.get("feed_url") or "")
        keywords = [str(item) for item in row.get("keywords", []) if item]
        sources.append(SourceConfig(
            name=str(row.get("name", "")),
            kind=kind,
            url=url,
            feed_url=feed_url,
            keywords=keywords,
        ))
    return sources
