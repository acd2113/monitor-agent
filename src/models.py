from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InterestTag:
    id: int
    tag: str
    description: str = ""
    priority: int = 0


@dataclass
class QueryPlan:
    topic: str
    tags: list[InterestTag] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    english_queries: list[str] = field(default_factory=list)
    chinese_queries: list[str] = field(default_factory=list)
    seed_urls: list[str] = field(default_factory=list)
    rss_urls: list[str] = field(default_factory=list)
    web_urls: list[str] = field(default_factory=list)
    max_age_days: int | None = None


@dataclass
class SourceItem:
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    published_missing: bool = True
    snippet: str = ""
    content: str = ""
    tier: int = 4
    guid: str = ""
    matched_tag: str = ""
    relevance: float | None = None
    relevance_reason: str = ""
    summary_zh: str = ""
    extra_sources: list[str] = field(default_factory=list)


@dataclass
class CollectionChannel:
    id: str
    name: str
    source_type: str
    queries: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    time_range: str = ""


@dataclass
class ToolOutput:
    text: str
    items: list[SourceItem] = field(default_factory=list)


@dataclass
class TimelineGroup:
    label: str
    items: list[SourceItem]


@dataclass
class MonitorSession:
    topic: str = ""
    plan: QueryPlan | None = None
    items: list[SourceItem] = field(default_factory=list)
    timeline: list[TimelineGroup] = field(default_factory=list)
    started_at: str = ""
