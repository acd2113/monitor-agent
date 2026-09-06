import json
from dataclasses import dataclass

import feedparser
import requests

from src.config import settings
from src.models import SourceItem, ToolOutput
from src.sources.base import hostname, parse_date, strip_html


@dataclass
class ParsedRSSItem:
    title: str
    url: str
    guid: str
    published_at: object
    published_missing: bool
    summary: str
    author: str


class RSSParser:
    def __init__(self, max_summary_length=500):
        self.max_summary_length = max_summary_length

    def parse(self, content, feed_url=""):
        content = (content or "").strip()
        if content.startswith("{"):
            try:
                data = json.loads(content)
                if "jsonfeed.org" in str(data.get("version", "")):
                    return self._parse_json_feed(data)
            except (json.JSONDecodeError, TypeError):
                pass

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"RSS parse failed: {feed.bozo_exception}")

        items = []
        for entry in feed.entries:
            item = self._parse_entry(entry)
            if item:
                items.append(item)
        return items

    def _parse_json_feed(self, data):
        items = []
        for row in data.get("items", []):
            title = strip_html(row.get("title", ""))
            url = row.get("url", "") or row.get("external_url", "")
            guid = row.get("id", "") or url
            summary = strip_html(row.get("summary") or row.get("content_text") or row.get("content_html"))
            published_at, published_missing = parse_date(row.get("date_published") or row.get("date_modified"))
            if not title and url:
                title = url
            if title:
                items.append(ParsedRSSItem(
                    title=title, url=url, guid=guid,
                    published_at=published_at, published_missing=published_missing,
                    summary=summary[: self.max_summary_length], author="",
                ))
        return items

    def _parse_entry(self, entry):
        title = strip_html(entry.get("title", ""))
        url = entry.get("link", "")
        if not url:
            for link in entry.get("links", []):
                if link.get("rel") == "alternate" or link.get("type", "").startswith("text/html"):
                    url = link.get("href", "")
                    break
            if not url and entry.get("links"):
                url = entry["links"][0].get("href", "")

        guid = entry.get("id") or entry.get("guid", "")
        if isinstance(guid, dict):
            guid = guid.get("value", "")
        published_at, published_missing = parse_date(entry.get("published_parsed") or entry.get("updated_parsed"))
        summary = entry.get("summary") or entry.get("description", "")
        if not summary:
            content = entry.get("content", [])
            if content and isinstance(content, list):
                summary = content[0].get("value", "")
        summary = strip_html(summary)
        if len(summary) > self.max_summary_length:
            summary = summary[: self.max_summary_length] + "..."
        author = strip_html(entry.get("author") or entry.get("dc_creator"))
        if not title and url:
            title = url
        if not title:
            return None
        return ParsedRSSItem(
            title=title, url=url, guid=guid,
            published_at=published_at, published_missing=published_missing,
            summary=summary, author=author,
        )


def fetch_rss(url):
    try:
        response = requests.get(
            url,
            timeout=settings.request_timeout,
            headers={"User-Agent": "MonitorAgent/1.0 RSS Reader"},
        )
        response.raise_for_status()
        parsed = RSSParser().parse(response.text, url)
        source = hostname(url)
        items = []
        lines = []
        for row in parsed:
            item = SourceItem(
                title=row.title,
                url=row.url,
                source=source,
                published_at=row.published_at,
                published_missing=row.published_missing,
                snippet=row.summary,
                content=row.summary,
                tier=3,
                guid=row.guid,
            )
            items.append(item)
            lines.append(f"{row.title}\n{row.url}\n{row.summary}")
        return ToolOutput(text="\n\n".join(lines), items=items)
    except Exception as exc:
        return ToolOutput(text=f"RSS fetch failed: {exc}", items=[])
