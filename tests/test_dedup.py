from datetime import datetime

from src.models import SourceItem
from src.pipeline.dedup import deduplicate, normalize_headline_key, normalize_url


def test_normalize_url():
    assert normalize_url("https://Example.com/path/?utm_source=x&b=2&a=1#frag") == "https://example.com/path?a=1&b=2"


def test_normalize_headline_key():
    key = normalize_headline_key("OpenAI Announces GPT-5!")
    assert key == "openai announces gpt"


def test_deduplicate_by_url():
    items = [
        SourceItem(title="Same", url="https://example.com/a?utm_source=1", source="s1", published_at=datetime(2026, 1, 2), published_missing=False),
        SourceItem(title="Same", url="https://example.com/a?utm_source=2", source="s2", published_at=datetime(2026, 1, 1), published_missing=False),
    ]
    result = deduplicate(items)
    assert len(result) == 1
    assert result[0].source == "s1"


def test_deduplicate_by_title():
    items = [
        SourceItem(title="OpenAI releases new model", url="https://a.com/1", source="a"),
        SourceItem(title="OpenAI releases new model!", url="https://b.com/2", source="b"),
    ]
    result = deduplicate(items)
    assert len(result) == 1


def test_deduplicate_by_content():
    content = "This is a long shared article body about the same event happening now."
    items = [
        SourceItem(title="Different title one", url="https://a.com/1", source="a", snippet=content, content=content),
        SourceItem(title="Completely different title", url="https://b.com/2", source="b", snippet=content, content=content),
    ]
    result = deduplicate(items)
    assert len(result) == 1
