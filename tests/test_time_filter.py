from datetime import datetime, timedelta, timezone

from src.models import SourceItem
from src.pipeline.time_filter import filter_by_recency, parse_time_window


def test_parse_time_window():
    assert parse_time_window("最新") == 3
    assert parse_time_window("最近") == 7
    assert parse_time_window("近期") == 14
    assert parse_time_window("近5天") == 5
    assert parse_time_window("普通主题") is None


def test_filter_by_recency():
    now = datetime.now(timezone.utc)
    fresh = SourceItem(
        title="fresh",
        url="https://a.com/1",
        source="a",
        published_at=now - timedelta(days=1),
        published_missing=False,
    )
    old = SourceItem(
        title="old",
        url="https://a.com/2",
        source="a",
        published_at=now - timedelta(days=10),
        published_missing=False,
    )
    missing = SourceItem(
        title="missing date",
        url="https://a.com/3",
        source="a",
        published_at=None,
        published_missing=True,
    )

    result = filter_by_recency([fresh, old, missing], 3)
    assert result == [fresh]
