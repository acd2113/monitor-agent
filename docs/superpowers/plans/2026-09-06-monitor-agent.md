# Monitor Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-run Textual topic monitoring agent that plans tags/queries, collects from Tavily/RSS/web, filters, deduplicates, classifies relevance, summarizes in Chinese, and shows a timeline.

**Architecture:** algocode-style fan-out collectors feeding a deterministic post-processing pipeline. Quality-first defaults are locked in `docs/superpowers/specs/2026-09-06-monitor-agent-design.md`.

**Tech Stack:** Python 3.13, Textual, OpenAI-compatible LLM, Tavily, feedparser, httpx, trafilatura, rapidfuzz, pytest.

---

### Task 1: Project skeleton and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `run_monitor.cmd`
- Create: `src/__init__.py`
- Create: `src/infrastructure/__init__.py`
- Create: `src/sources/__init__.py`
- Create: `src/agent/__init__.py`
- Create: `src/pipeline/__init__.py`
- Create: `src/tui/__init__.py`

- [ ] Create all package directories and initializer files.
- [ ] Add `requirements.txt` with openai, python-dotenv, tavily-python, feedparser, httpx, trafilatura, beautifulsoup4, rapidfuzz, textual, pytest.
- [ ] Add `.env.example` with LLM/Tavily/RSS/threshold keys.
- [ ] Verify imports with a smoke command after installing dependencies.

### Task 2: Config and data models

**Files:**
- Create: `src/config.py`
- Create: `src/models.py`
- Test: `tests/test_config.py`

- [ ] Write `Settings` class reading `.env` and exposing quality-first defaults.
- [ ] Write `InterestTag`, `QueryPlan`, `SourceItem`, `CollectionChannel`, `ToolOutput`, `MonitorSession`.
- [ ] Write a config test asserting defaults and env override behavior.

### Task 3: LLM client and prompt templates

**Files:**
- Create: `src/infrastructure/llm_client.py`
- Create: `src/prompts.py`
- Test: `tests/test_json_utils.py`

- [ ] Write `LLMClient` using OpenAI SDK with configurable base URL, API key, model, timeout, retries.
- [ ] Add `chat_json` helper that requests JSON and parses robustly.
- [ ] Add English prompts for planner, classification, and summary.
- [ ] Add JSON cleanup utilities (`clean_json_tags`, `extract_clean_response`, `fix_incomplete_json`).

### Task 4: Source implementations

**Files:**
- Create: `src/sources/base.py`
- Create: `src/sources/tavily.py`
- Create: `src/sources/rss.py`
- Create: `src/sources/web.py`
- Test: `tests/test_rss.py`

- [ ] Define `ToolOutput` contract and source helpers.
- [ ] Implement Tavily search returning `SourceItem` list with retries.
- [ ] Implement RSS/Atom/JSON Feed parser using feedparser plus manual date and text cleanup.
- [ ] Implement web fetch with trafilatura and BeautifulSoup fallback.
- [ ] Write RSS parsing tests for RSS, Atom, JSON Feed, and missing dates.

### Task 5: Collector agent loop

**Files:**
- Create: `src/agent/collector.py`
- Test: `tests/test_collector.py`

- [ ] Define tool schemas for `search_web`, `fetch_rss`, `fetch_web`.
- [ ] Implement bounded tool loop with round/search budgets and tool-result caching.
- [ ] Collect structured `SourceItem` objects through tool side effects.
- [ ] Write collector tests using fake tools.

### Task 6: Planner and keyword filter

**Files:**
- Create: `src/pipeline/planner.py`
- Create: `src/pipeline/keyword_filter.py`
- Test: `tests/test_keyword_filter.py`

- [ ] Implement `plan(topic)` extracting tags, keywords, queries, and seed URLs.
- [ ] Implement configurable hard filter with normal, required, excluded, regex, and max-count rules.
- [ ] Write filter tests for the rule grammar.

### Task 7: Deduplication

**Files:**
- Create: `src/pipeline/dedup.py`
- Test: `tests/test_dedup.py`

- [ ] Implement URL/GUID normalization.
- [ ] Implement exact duplicate removal.
- [ ] Implement title fuzzy deduplication with rapidfuzz.
- [ ] Implement content shingling and Jaccard deduplication.
- [ ] Implement weighted primary selection and source merging.
- [ ] Write dedup tests covering URL, title, content, and primary selection.

### Task 8: Relevance, summary, and timeline

**Files:**
- Create: `src/pipeline/relevance.py`
- Create: `src/pipeline/summary.py`
- Create: `src/pipeline/timeline.py`

- [ ] Implement batched tag classification with score threshold.
- [ ] Implement batched Chinese summary with snippet fallback.
- [ ] Implement time-based sorting and day grouping with missing dates last.

### Task 9: Orchestrator and end-to-end pipeline

**Files:**
- Create: `src/pipeline/orchestrator.py`
- Test: `tests/test_pipeline.py`

- [ ] Implement `MonitorOrchestrator.run(topic, on_event=None)`.
- [ ] Wire planner, collectors, filter, dedup, relevance, summary, timeline.
- [ ] Write end-to-end test with mocked LLM and sources.

### Task 10: Textual UI and entrypoint

**Files:**
- Create: `src/tui/tui_app.py`
- Create: `run_monitor.cmd`

- [ ] Implement a Textual app with input, status, and results table.
- [ ] Run the orchestrator in a worker thread and stream status events.
- [ ] Add Windows entrypoint script.
- [ ] Run local UI smoke test.
