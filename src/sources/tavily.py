from tavily import TavilyClient

from src.config import settings
from src.models import SourceItem, ToolOutput
from src.sources.base import parse_date


def search_web(query, max_results=None, time_range=None):
    if not settings.tavily_api_key:
        return ToolOutput(text="Tavily API key not configured.", items=[])

    max_results = max_results or settings.max_results_per_source
    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        kwargs = {
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "topic": "general",
            "include_answer": False,
        }
        if time_range:
            kwargs["time_range"] = time_range
        response = client.search(**kwargs)
        results = response.get("results", []) if isinstance(response, dict) else []
    except Exception as exc:
        return ToolOutput(text=f"Tavily search failed: {exc}", items=[])

    items = []
    lines = []
    for row in results:
        title = row.get("title", "")
        url = row.get("url", "")
        content = row.get("content", "")
        published_at, published_missing = parse_date(row.get("published_date"))
        score = row.get("score")
        item = SourceItem(
            title=title,
            url=url,
            source="tavily",
            published_at=published_at,
            published_missing=published_missing,
            snippet=content,
            content=content,
            tier=4,
            relevance=score,
        )
        items.append(item)
        lines.append(f"{title}\n{url}\n{content}")

    return ToolOutput(text="\n\n".join(lines), items=items)
