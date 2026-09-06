import json

from src.config import settings
from src.prompts import SUMMARY_SYSTEM_PROMPT


def summarize_items(client, items, on_item=None):
    if not items:
        return []

    for item in items:
        item.summary_zh = item.snippet or item.title

    emitted = set()

    for start in range(0, len(items), settings.classify_batch_size):
        batch = items[start : start + settings.classify_batch_size]
        payload = {
            "items": [
                {
                    "id": index,
                    "title": item.title,
                    "snippet": item.snippet[:300],
                    "content": (item.content or item.snippet)[:500],
                }
                for index, item in enumerate(batch)
            ]
        }
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
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
            summary = str(row.get("summary", "")).strip()
            if summary:
                batch[index].summary_zh = summary
            if on_item and id(batch[index]) not in emitted:
                emitted.add(id(batch[index]))
                on_item(batch[index])

    if on_item:
        for item in items:
            if id(item) not in emitted:
                emitted.add(id(item))
                on_item(item)

    return items
