import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self):
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_base_url = os.getenv("LLM_BASE_URL", "").strip()
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_timeout = _int("LLM_TIMEOUT", 180)

        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.github_api_key = os.getenv("GITHUB_API_KEY", "")
        self.rss_feeds = self._split_feeds(os.getenv("RSS_FEEDS", ""))
        self.keyword_filter_file = os.getenv("KEYWORD_FILTER_FILE", "")
        self.sources_file = os.getenv("SOURCES_FILE", "sources.json")

        self.max_search_rounds = _int("MAX_SEARCH_ROUNDS", 4)
        self.max_web_searches = _int("MAX_WEB_SEARCHES", 6)
        self.max_results_per_source = _int("MAX_RESULTS_PER_SOURCE", 8)
        self.relevance_threshold = _float("RELEVANCE_THRESHOLD", 0.8)
        self.classify_batch_size = _int("CLASSIFY_BATCH_SIZE", 20)
        self.title_sim_threshold = _float("TITLE_SIM_THRESHOLD", 0.90)
        self.content_jaccard_threshold = _float("CONTENT_JACCARD_THRESHOLD", 0.88)
        self.min_tags = _int("MIN_TAGS", 5)
        self.max_tags = _int("MAX_TAGS", 12)
        self.request_timeout = _int("REQUEST_TIMEOUT", 30)
        self.max_retries = _int("MAX_RETRIES", 2)

    def _split_feeds(self, raw):
        feeds = []
        for part in (raw or "").split(","):
            url = part.strip()
            if url:
                feeds.append(url)
        return feeds


settings = Settings()
