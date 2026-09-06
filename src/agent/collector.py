import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import settings
from src.models import ToolOutput
from src.prompts import COLLECTOR_SYSTEM_PROMPT
from src.sources.base import hostname
from src.sources.github import fetch_github, repo_from_url
from src.sources.rss import fetch_rss
from src.sources.tavily import search_web
from src.sources.web import fetch_web

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web with Tavily for a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_rss",
            "description": "Fetch and parse an RSS/Atom/JSON feed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Feed URL"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_web",
            "description": "Fetch a web page and extract its main content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Page URL"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_github",
            "description": "Fetch latest releases and commits from a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "GitHub repository URL"},
                },
                "required": ["url"],
            },
        },
    },
]


class CollectorAgent:
    def __init__(self, client, channel, on_channel_event=None):
        self.client = client
        self.channel = channel
        self.on_channel_event = on_channel_event
        self.collected = []
        self.web_searches = 0
        self.tool_cache = {}

    def _emit(self, kind, text):
        if self.on_channel_event:
            self.on_channel_event(self.channel.id, kind, text)

    def _allowed_tools(self):
        if self.channel.source_type == "tavily":
            return ["search_web"]
        if self.channel.source_type == "rss":
            return ["fetch_rss"]
        if self.channel.source_type == "web":
            return ["fetch_web", "fetch_github"]
        return ["search_web", "fetch_rss", "fetch_web", "fetch_github"]

    def _tools(self):
        allowed = set(self._allowed_tools())
        return [spec for spec in TOOL_SPECS if spec["function"]["name"] in allowed]

    def _tool_label(self, name, args):
        if name == "search_web":
            return f"调用工具 search_web [{args.get('query', '')}]"
        if name == "fetch_rss":
            url = args.get("url", "")
            return f"调用工具 fetch_rss [{hostname(url)}]"
        if name == "fetch_web":
            return f"调用工具 fetch_web [{args.get('url', '')}]"
        if name == "fetch_github":
            owner, repo = repo_from_url(args.get("url", ""))
            label = f"{owner}/{repo}" if owner and repo else args.get("url", "")
            return f"调用工具 fetch_github [{label}]"
        return f"调用工具 {name}"

    def _execute_tool(self, name, arguments_json):
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except (json.JSONDecodeError, TypeError):
            args = {}

        key = (name, arguments_json or "{}")
        if key in self.tool_cache:
            return self.tool_cache[key]

        if name == "search_web":
            if self.web_searches >= settings.max_web_searches:
                output = ToolOutput(text="Search budget exhausted.", items=[])
            else:
                self.web_searches += 1
                output = search_web(args.get("query", ""), time_range=self.channel.time_range)
        elif name == "fetch_rss":
            output = fetch_rss(args.get("url", ""))
        elif name == "fetch_web":
            output = fetch_web(args.get("url", ""))
        elif name == "fetch_github":
            output = fetch_github(args.get("url", ""))
        else:
            output = ToolOutput(text=f"Unknown tool: {name}", items=[])

        self.collected.extend(output.items)
        for item in output.items:
            self._emit("item", item.title)
        self.tool_cache[key] = output.text
        return output.text

    def collect(self):
        if not self.channel.queries and not self.channel.urls:
            self._emit("done", "完成")
            return self.collected

        prompt = (
            f"Channel: {self.channel.name}\n"
            f"Source type: {self.channel.source_type}\n"
            f"Queries: {json.dumps(self.channel.queries, ensure_ascii=False)}\n"
            f"URLs: {json.dumps(self.channel.urls, ensure_ascii=False)}\n"
            "Gather relevant items."
        )
        messages = [
            {"role": "system", "content": COLLECTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        tools = self._tools()

        for round_no in range(settings.max_search_rounds + 1):
            self._emit("reasoning", "")
            try:
                response = self.client.client.chat.completions.create(
                    model=self.client.model,
                    messages=messages,
                    temperature=0.1,
                    tools=tools,
                )
                choice = response.choices[0]
            except Exception as exc:
                self._emit("error", f"LLM 失败：{exc}")
                break

            tool_calls = choice.message.tool_calls or []
            if not tool_calls:
                break

            messages.append({
                "role": "assistant",
                "content": choice.message.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, TypeError):
                    args = {}
                self._emit("tool", self._tool_label(tc.function.name, args))
                result = self._execute_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        self._emit("done", "完成")
        return self.collected


def collect_all(client, channels, on_channel_event=None):
    if not channels:
        return []
    results = {}
    with ThreadPoolExecutor(max_workers=min(len(channels), 4)) as executor:
        futures = {}
        for channel in channels:
            agent = CollectorAgent(client, channel, on_channel_event)
            futures[executor.submit(agent.collect)] = channel.id

        for future in as_completed(futures):
            channel_id = futures[future]
            try:
                results[channel_id] = future.result()
            except Exception:
                results[channel_id] = []

    merged = []
    for channel in channels:
        merged.extend(results.get(channel.id, []))
    return merged
