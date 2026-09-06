import json

from src.config import settings
from src.models import InterestTag, QueryPlan
from src.pipeline.time_filter import parse_time_window
from src.prompts import PLANNER_SYSTEM_PROMPT
from src.sources.registry import load_sources


def _fallback_sources(sources, plan):
    terms = [plan.topic]
    terms.extend(plan.keywords)
    terms.extend([tag.tag for tag in plan.tags])
    terms = [term.lower() for term in terms if term]

    rss_urls = []
    web_urls = []
    for source in sources:
        haystack = [source.name] + list(source.keywords)
        relevant = any(
            term in item.lower() or item.lower() in term
            for term in terms
            for item in haystack
        )
        if not relevant:
            continue
        if source.kind == "rss":
            rss_urls.append(source.feed_url or source.url)
        elif source.kind == "web":
            web_urls.append(source.url)
    return rss_urls, web_urls


def plan(topic, client):
    sources = load_sources(settings.sources_file)
    source_payload = [
        {
            "name": source.name,
            "kind": source.kind,
            "feed_url": source.feed_url,
            "url": source.url,
            "keywords": source.keywords,
        }
        for source in sources
    ]

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Topic:\n{topic}\n\nAvailable sources:\n{json.dumps(source_payload, ensure_ascii=False)}",
        },
    ]
    data = client.chat_json(messages)
    if not isinstance(data, dict):
        data = {}

    tags = []
    for index, row in enumerate(data.get("tags", [])):
        if not isinstance(row, dict) or not row.get("tag"):
            continue
        tags.append(InterestTag(
            id=index + 1,
            tag=str(row["tag"]),
            description=str(row.get("description", "")),
            priority=index + 1,
        ))

    tags = tags[: settings.max_tags]
    if len(tags) < settings.min_tags:
        tags.append(InterestTag(
            id=len(tags) + 1,
            tag="通用",
            description="与主题相关的内容",
            priority=len(tags) + 1,
        ))

    keywords = [str(item) for item in data.get("keywords", []) if item]
    english_queries = [str(item) for item in data.get("english_queries", []) if item]
    chinese_queries = [str(item) for item in data.get("chinese_queries", []) if item]
    seed_urls = [str(item) for item in data.get("seed_urls", []) if item]
    rss_urls = [str(item) for item in data.get("rss_urls", []) if item]
    web_urls = [str(item) for item in data.get("web_urls", []) if item]

    if not english_queries and not chinese_queries:
        english_queries = [topic]
    if not keywords:
        keywords = [topic]

    fallback_plan = QueryPlan(topic=topic, tags=tags, keywords=keywords)
    fallback_rss, fallback_web = _fallback_sources(sources, fallback_plan)
    if not rss_urls:
        rss_urls = fallback_rss
    if not web_urls:
        web_urls = fallback_web

    return QueryPlan(
        topic=topic,
        tags=tags,
        keywords=keywords,
        english_queries=english_queries,
        chinese_queries=chinese_queries,
        seed_urls=seed_urls,
        rss_urls=list(dict.fromkeys(rss_urls)),
        web_urls=list(dict.fromkeys(web_urls)),
        max_age_days=parse_time_window(topic),
    )
