import threading
import time

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, RichLog, Static

from src.config import settings
from src.infrastructure.llm_client import LLMClient
from src.pipeline.orchestrator import MonitorOrchestrator
from src.sources.base import hostname

SPINNER = ["◐", "◓", "◑", "◒"]
CHANNEL_NAMES = {
    "en_search": "英文搜索",
    "zh_search": "中文搜索",
    "rss": "RSS 源",
    "web": "网页/官方源",
}


class CollectorPanel(Vertical):
    def __init__(self, channel_id, channel_name, **kwargs):
        super().__init__(**kwargs)
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.collapsed = False
        self._item_count = 0
        self._items = []
        self._thinking = False
        self._spin_idx = 0
        self._think_timer = None

    def compose(self) -> ComposeResult:
        yield Static(f"▾ {self.channel_name}", id="panel-title")
        yield Static("", id="panel-thinking")
        yield RichLog(wrap=True, highlight=True, markup=False, id="panel-detail", auto_scroll=False)
        yield RichLog(wrap=True, highlight=True, markup=False, id="panel-log", auto_scroll=False)

    def on_mount(self):
        self.query_one("#panel-detail", RichLog).display = False
        self.query_one("#panel-thinking", Static).display = False

    def _start_thinking(self):
        if self._thinking:
            return
        self._thinking = True
        self._spin_idx = 0
        box = self.query_one("#panel-thinking", Static)
        box.display = True
        box.update(f"{SPINNER[0]} 思考中")
        self._think_timer = self.set_interval(0.12, self._tick_thinking)

    def _tick_thinking(self):
        self._spin_idx = (self._spin_idx + 1) % len(SPINNER)
        self.query_one("#panel-thinking", Static).update(f"{SPINNER[self._spin_idx]} 思考中")

    def _stop_thinking(self):
        if not self._thinking:
            return
        self._thinking = False
        if self._think_timer is not None:
            try:
                self._think_timer.stop()
            except Exception:
                pass
            self._think_timer = None
        self.query_one("#panel-thinking", Static).display = False

    def set_collapsed(self, collapsed):
        if self.collapsed == collapsed:
            return
        self.toggle_collapse()

    def toggle_collapse(self):
        self.collapsed = not self.collapsed
        title = self.query_one("#panel-title", Static)
        title.update((("▸ " if self.collapsed else "▾ ") + self.channel_name))
        detail = self.query_one("#panel-detail", RichLog)
        log = self.query_one("#panel-log", RichLog)
        detail.display = self.collapsed
        log.display = not self.collapsed
        if self.collapsed:
            self._render_detail()

    def _render_detail(self):
        detail = self.query_one("#panel-detail", RichLog)
        detail.clear()
        detail.write(f"已获信息 {self._item_count} 条")
        for item in self._items[-12:]:
            detail.write(f"- {item}")

    def push(self, kind, text):
        if kind == "reasoning":
            self._start_thinking()
            return
        self._stop_thinking()
        if kind == "item":
            self._item_count += 1
            self._items.append(text)
            if self.collapsed:
                self._render_detail()
            else:
                self.query_one("#panel-log", RichLog).write(f"已获取：{text}")
        elif kind == "error":
            self.query_one("#panel-log", RichLog).write(f"错误：{text}")
        else:
            self.query_one("#panel-log", RichLog).write(text)

    def on_click(self, event):
        self.toggle_collapse()


class MonitorApp(App):
    TITLE = "MonitorAgent"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("ctrl+q", "quit", "退出"),
        ("ctrl+h", "toggle_all_panels", "收起/展开全部面板"),
    ]

    CSS = """
    Screen {
        background: #020617;
        color: #F8FAFC;
    }

    #topbar {
        height: 3;
        background: transparent;
        color: #22C55E;
        padding: 1 2;
        text-style: bold;
        border-bottom: solid #22C55E;
    }

    #main {
        padding: 1 2 0 2;
        background: transparent;
        height: 1fr;
    }

    #sidebar {
        width: 42;
        height: 1fr;
        background: transparent;
        padding: 1;
        margin: 0 1 0 0;
    }

    #topic-title, #side-title, #plan-title {
        color: #22C55E;
        text-style: bold;
        margin-bottom: 1;
    }

    #current-topic {
        height: 3;
        color: #F8FAFC;
        background: transparent;
        border: round #334155;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    #status {
        height: 5;
        color: #CBD5E1;
        background: transparent;
        border: round #334155;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    #plan-title {
        margin-top: 1;
    }

    #plan-info {
        height: 14;
        color: #CBD5E1;
        background: transparent;
        border: round #334155;
        padding: 0 1;
    }

    #workspace {
        width: 1fr;
        height: 1fr;
        background: transparent;
        padding: 1;
    }

    #panels {
        display: none;
        height: auto;
        min-height: 6;
        margin: 0 0 1 0;
        background: transparent;
    }

    CollectorPanel {
        width: 1fr;
        border: round #334155;
        margin: 0 1;
        background: transparent;
    }

    CollectorPanel:first-of-type {
        margin-left: 0;
    }

    #panel-title {
        background: transparent;
        color: #22C55E;
        text-style: bold;
        padding: 0 1;
        height: 1;
    }

    #panel-thinking {
        color: #38BDF8;
        text-style: italic;
        padding: 0 1;
        background: transparent;
    }

    #panel-detail {
        color: #CBD5E1;
        background: transparent;
        border-top: solid #334155;
    }

    #panel-log {
        background: transparent;
        color: #F8FAFC;
    }

    #results {
        background: transparent;
        color: #F8FAFC;
        border: round #334155;
        height: 1fr;
    }

    #topic {
        border: round #22C55E;
        background: transparent;
        color: #F8FAFC;
        height: 3;
        margin: 0 2 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("◤ MonitorAgent   信息监控 Agent  ·  Enter 提交  ·  Ctrl+Q 退出", id="topbar"),
            Horizontal(
                Vertical(
                    Static("监控主题", id="topic-title"),
                    Static("等待输入", id="current-topic"),
                    Static("运行状态", id="side-title"),
                    Static("等待输入主题", id="status"),
                    Static("规划信息", id="plan-title"),
                    RichLog(wrap=True, highlight=True, markup=False, id="plan-info", auto_scroll=True),
                    id="sidebar",
                ),
                Vertical(
                    Horizontal(id="panels"),
                    DataTable(id="results"),
                    id="workspace",
                ),
                id="main",
            ),
            Input(placeholder="输入主题，按 Enter 提交", id="topic"),
        )

    def on_mount(self):
        table = self.query_one("#results", DataTable)
        table.add_columns("时间", "标签", "来源", "标题", "摘要")
        self.panels = {}
        self._status_text = "等待输入主题"
        self._status_spinner_idx = 0
        self._status_timer = None
        self.query_one("#topic", Input).focus()

    def _status_line(self):
        if self._status_timer is not None:
            return f"{self._status_text} {SPINNER[self._status_spinner_idx]}"
        return self._status_text

    def _start_status_spinner(self):
        if self._status_timer is not None:
            return
        self._status_spinner_idx = 0
        self._status_timer = self.set_interval(0.12, self._tick_status_spinner)
        self.query_one("#status", Static).update(self._status_line())

    def _tick_status_spinner(self):
        self._status_spinner_idx = (self._status_spinner_idx + 1) % len(SPINNER)
        self.query_one("#status", Static).update(self._status_line())

    def _stop_status_spinner(self):
        if self._status_timer is not None:
            try:
                self._status_timer.stop()
            except Exception:
                pass
            self._status_timer = None

    def _set_status_text(self, text):
        self._status_text = text
        self.query_one("#status", Static).update(self._status_line())

    def on_input_submitted(self, event):
        if getattr(event.input, "id", "") != "topic":
            return
        topic = event.input.value.strip()
        event.input.value = ""
        if not topic:
            self._stop_status_spinner()
            self._status_text = "请输入主题"
            self.query_one("#status", Static).update(self._status_text)
            return

        self.query_one("#current-topic", Static).update(topic)

        missing = []
        if not settings.llm_api_key:
            missing.append("LLM_API_KEY")
        if not settings.tavily_api_key:
            missing.append("TAVILY_API_KEY")
        if missing:
            self._stop_status_spinner()
            self._status_text = f"请先在 .env 中配置：{', '.join(missing)}"
            self.query_one("#status", Static).update(self._status_text)
            return

        self._run_topic(topic)

    def action_toggle_all_panels(self):
        if not self.panels:
            return
        should_collapse = any(not panel.collapsed for panel in self.panels.values())
        for panel in self.panels.values():
            panel.set_collapsed(should_collapse)

    def _collapse_all_panels(self):
        for panel in self.panels.values():
            panel.set_collapsed(True)

    def _render_plan(self, plan):
        tags = "、".join([tag.tag for tag in plan.tags]) or "无"
        rss_info = "\n".join([f"- {hostname(url)}" for url in plan.rss_urls]) or "- 无"
        web_info = "\n".join([f"- {hostname(url)}" for url in plan.web_urls]) or "- 无"
        lines = [
            f"标签：{tags}",
            f"关键词：{', '.join(plan.keywords) or '无'}",
            f"英文查询：{', '.join(plan.english_queries) or '无'}",
            f"中文查询：{', '.join(plan.chinese_queries) or '无'}",
            f"RSS 源：\n{rss_info}",
            f"网页源：\n{web_info}",
            f"时间窗口：{plan.max_age_days if plan.max_age_days else '不限'}",
        ]
        info = self.query_one("#plan-info", RichLog)
        info.clear()
        info.write("\n".join(lines))

    def _run_topic(self, topic):
        self._status_text = "开始运行..."
        self._start_status_spinner()
        status = self.query_one("#status", Static)
        panels = self.query_one("#panels", Horizontal)
        panels.remove_children()
        panels.display = True
        self.panels = {}

        plan_info = self.query_one("#plan-info", RichLog)
        plan_info.clear()
        plan_info.write("正在规划...")

        def on_event(kind, text):
            self.call_from_thread(self._set_status_text, text)

        def on_plan(plan):
            self.call_from_thread(self._render_plan, plan)

        def on_channel_event(channel_id, kind, text):
            self.call_from_thread(self._handle_channel_event, channel_id, kind, text)

        def worker():
            try:
                client = LLMClient()
                session = MonitorOrchestrator(client).run(
                    topic,
                    on_event=on_event,
                    on_channel_event=on_channel_event,
                    on_plan=on_plan,
                )
                self.call_from_thread(self._render_session, session)
            except Exception as exc:
                self.call_from_thread(self._set_status_text, f"运行失败：{exc}")
                self.call_from_thread(self._stop_status_spinner)

        threading.Thread(target=worker, daemon=True).start()

    def _ensure_panel(self, channel_id):
        if channel_id in self.panels:
            return self.panels[channel_id]
        panel = CollectorPanel(channel_id, CHANNEL_NAMES.get(channel_id, channel_id))
        self.query_one("#panels", Horizontal).mount(panel)
        self.panels[channel_id] = panel
        return panel

    def _handle_channel_event(self, channel_id, kind, text):
        self._ensure_panel(channel_id).push(kind, text)

    def _render_session(self, session):
        self._stop_status_spinner()
        self._status_text = f"完成，共 {len(session.items)} 条"
        self.query_one("#status", Static).update(self._status_text)

        table = self.query_one("#results", DataTable)
        table.clear()
        for group in session.timeline:
            for item in group.items:
                time_text = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else ""
                table.add_row(
                    time_text,
                    item.matched_tag,
                    item.source,
                    item.title,
                    item.summary_zh or item.snippet or "",
                )

        panels = self.query_one("#panels", Horizontal)
        self._collapse_all_panels()
        panels.remove_children()
        panels.display = False
        self.panels = {}


def main():
    MonitorApp().run()


if __name__ == "__main__":
    main()
