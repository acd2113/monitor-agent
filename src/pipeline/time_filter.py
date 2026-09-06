import re
from datetime import datetime, timedelta, timezone


def parse_time_window(topic):
    text = (topic or "").lower()

    match = re.search(r"(?:近|过去|最近|last|past)\s*(\d+)\s*(?:天|日|day|days)", text)
    if match:
        return int(match.group(1))

    if any(word in text for word in ("24小时", "24 hours", "今天", "today")):
        return 1
    if any(word in text for word in ("最新", "latest")):
        return 3
    if any(word in text for word in ("最近", "recent")):
        return 7
    if any(word in text for word in ("近期", "recently")):
        return 14
    if any(word in text for word in ("本周", "this week")):
        return 7
    if any(word in text for word in ("本月", "this month")):
        return 30
    return None


def filter_by_recency(items, max_age_days):
    if not max_age_days:
        return items

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)

    fresh = []
    missing = []

    for item in items:
        published = item.published_at
        if published is None or item.published_missing:
            missing.append(item)
            continue
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            fresh.append(item)

    if fresh:
        return fresh
    return missing
