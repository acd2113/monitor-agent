from datetime import datetime

from src.agent.collector import collect_all
from src.config import settings
from src.models import CollectionChannel, MonitorSession
from src.pipeline.dedup import deduplicate
from src.pipeline.keyword_filter import filter_items
from src.pipeline.planner import plan
from src.pipeline.relevance import classify_items
from src.pipeline.summary import summarize_items
from src.pipeline.time_filter import filter_by_recency
from src.pipeline.timeline import build_timeline


def _time_range(max_age_days):
    if max_age_days is None:
        return ""
    if max_age_days <= 1:
        return "d"
    if max_age_days <= 7:
        return "w"
    if max_age_days <= 30:
        return "m"
    return ""


def build_channels(plan):
    time_range = _time_range(plan.max_age_days)

    rss_urls = list(settings.rss_feeds)
    rss_urls.extend(plan.rss_urls)

    web_urls = list(plan.seed_urls)
    web_urls.extend(plan.web_urls)

    rss_urls = list(dict.fromkeys([url for url in rss_urls if url]))
    web_urls = list(dict.fromkeys([url for url in web_urls if url]))

    channels = []
    if plan.english_queries:
        channels.append(CollectionChannel(
            id="en_search",
            name="英文搜索",
            source_type="tavily",
            queries=plan.english_queries,
            time_range=time_range,
        ))
    if plan.chinese_queries:
        channels.append(CollectionChannel(
            id="zh_search",
            name="中文搜索",
            source_type="tavily",
            queries=plan.chinese_queries,
            time_range=time_range,
        ))
    if rss_urls:
        channels.append(CollectionChannel(
            id="rss",
            name="RSS 源",
            source_type="rss",
            queries=plan.keywords,
            urls=rss_urls,
        ))
    if web_urls:
        channels.append(CollectionChannel(
            id="web",
            name="网页/官方源",
            source_type="web",
            urls=web_urls,
        ))
    return channels


class MonitorOrchestrator:
    def __init__(self, client):
        self.client = client

    def run(self, topic, on_event=None, on_channel_event=None, on_plan=None, on_item=None):
        session = MonitorSession(
            topic=topic,
            started_at=datetime.now().isoformat(timespec="seconds"),
        )

        def emit(text):
            if on_event:
                on_event("status", text)

        emit("正在提取标签和查询词...")
        session.plan = plan(topic, self.client)
        if on_plan:
            on_plan(session.plan)
        channels = build_channels(session.plan)

        emit(f"正在采集 {len(channels)} 个通道...")
        items = collect_all(self.client, channels, on_channel_event=on_channel_event)
        emit(f"采集到 {len(items)} 条，正在按时间过滤...")

        items = filter_by_recency(items, session.plan.max_age_days)
        emit(f"时间过滤后 {len(items)} 条，正在规则过滤...")

        if settings.keyword_filter_file:
            items = filter_items(items, settings.keyword_filter_file)

        items = deduplicate(items)
        emit(f"去重后 {len(items)} 条，正在判断相关性...")

        items = classify_items(self.client, session.plan.topic, session.plan.tags, items)
        emit(f"相关条目 {len(items)} 条，正在生成摘要...")

        items = summarize_items(self.client, items, on_item=on_item)
        session.items = items
        session.timeline = build_timeline(items)
        emit("完成")
        return session
