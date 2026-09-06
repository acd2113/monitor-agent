import html
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from rapidfuzz import fuzz

from src.config import settings


def normalize_url(url):
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "fbclid", "gclid"))
    ]
    query = urlencode(sorted(query_pairs))
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_headline_key(title):
    text = html.unescape(title or "")
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [word for word in text.split() if len(word) > 2]
    return " ".join(tokens[:8])


def shingles(text, k=4):
    text = html.unescape(text or "").lower()
    tokens = re.findall(r"[a-z0-9\u4e00-\u9fff]+", text)
    if len(tokens) < k:
        return set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(left, right):
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 0.0
    return len(left & right) / union


def _item_key(item):
    return item.guid or normalize_url(item.url) or normalize_headline_key(item.title)


def _primary(cluster):
    def sort_key(item):
        has_date = bool(item.published_at and not item.published_missing)
        timestamp = item.published_at.timestamp() if has_date else 0.0
        return (
            item.tier,
            0 if has_date else 1,
            -timestamp,
            -len(item.content or ""),
            -(item.relevance if item.relevance is not None else 0.0),
        )
    return sorted(cluster, key=sort_key)[0]


def deduplicate(items, title_threshold=None, content_threshold=None):
    title_threshold = title_threshold if title_threshold is not None else settings.title_sim_threshold
    content_threshold = content_threshold if content_threshold is not None else settings.content_jaccard_threshold

    exact_groups = {}
    for item in items:
        key = _item_key(item) or f"__{id(item)}"
        exact_groups.setdefault(key, []).append(item)

    title_groups = list(exact_groups.values())

    title_merged = []
    for group in title_groups:
        rep = group[0]
        placed = False
        for existing in title_merged:
            ratio = fuzz.token_set_ratio(rep.title, existing[0].title) / 100.0
            if ratio >= title_threshold:
                existing.extend(group)
                placed = True
                break
        if not placed:
            title_merged.append(group)

    content_merged = []
    for group in title_merged:
        rep = group[0]
        placed = False
        rep_shingles = shingles(rep.content or rep.snippet)
        for existing in content_merged:
            existing_shingles = shingles(existing[0].content or existing[0].snippet)
            if rep_shingles and existing_shingles and jaccard(rep_shingles, existing_shingles) >= content_threshold:
                existing.extend(group)
                placed = True
                break
        if not placed:
            content_merged.append(group)

    result = []
    for group in content_merged:
        primary = _primary(group)
        for other in group:
            if other is not primary and other.source and other.source not in primary.extra_sources:
                primary.extra_sources.append(other.source)
        result.append(primary)
    return result
