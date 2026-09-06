import httpx
import trafilatura
from bs4 import BeautifulSoup

from src.config import settings
from src.models import SourceItem, ToolOutput
from src.sources.base import hostname, parse_date, strip_html


def _extract_meta_date(soup):
    for name in ("article:published_time", "og:published_time", "date"):
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return parse_date(tag["content"])
    return None, True


def fetch_web(url):
    try:
        response = httpx.get(
            url,
            timeout=settings.request_timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 MonitorAgent/1.0"},
        )
        response.raise_for_status()
        html = response.text
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        if not text:
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
        text = strip_html(text or "")
        snippet = text[:500]
        published_at, published_missing = _extract_meta_date(soup)
        item = SourceItem(
            title=title,
            url=url,
            source=hostname(url),
            published_at=published_at,
            published_missing=published_missing,
            snippet=snippet,
            content=text,
            tier=3,
        )
        return ToolOutput(text=f"{title}\n{url}\n{snippet}", items=[item])
    except Exception as exc:
        return ToolOutput(text=f"Web fetch failed: {exc}", items=[])
