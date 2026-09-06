from collections import defaultdict
from datetime import datetime, timezone

from src.models import TimelineGroup


def _sort_datetime(item):
    published = item.published_at
    if published is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if published.tzinfo is None:
        return published.replace(tzinfo=timezone.utc)
    return published


def build_timeline(items):
    groups = defaultdict(list)
    for item in items:
        if item.published_at and not item.published_missing:
            label = item.published_at.strftime("%Y-%m-%d")
        else:
            label = "未知时间"
        groups[label].append(item)

    for group in groups.values():
        group.sort(key=_sort_datetime, reverse=True)

    known = sorted([label for label in groups if label != "未知时间"], reverse=True)
    labels = known + (["未知时间"] if "未知时间" in groups else [])
    return [TimelineGroup(label=label, items=groups[label]) for label in labels]
