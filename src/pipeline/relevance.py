import json

from src.config import settings
from src.prompts import CLASSIFY_SYSTEM_PROMPT


def classify_items(client, topic, tags, items):
    if not items:
        return []

    for item in items:
        item.matched_tag = "通用"
        item.relevance = 1.0

    for start in range(0, len(items), settings.classify_batch_size):
        batch = items[start : start + settings.classify_batch_size]
        payload = {
            "topic": topic,
            "items": [
                {
                    "id": index,
                    "title": item.title,
                    "summary": item.snippet[:300],
                    "content": (item.content or item.snippet)[:500],
                }
                for index, item in enumerate(batch)
            ],
        }
        messages = [
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        data = client.chat_json(messages)
        if not isinstance(data, dict):
            continue

        for row in data.get("results", []):
            if not isinstance(row, dict):
                continue
            try:
                index = int(row.get("id", -1))
            except (TypeError, ValueError):
                continue
            if index < 0 or index >= len(batch):
                continue
            keep = bool(row.get("keep", False))
            batch[index].relevance = 1.0 if keep else 0.0

    return [item for item in items if item.relevance == 1.0]
