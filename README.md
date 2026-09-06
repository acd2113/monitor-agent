# MonitorAgent 信息监控 Agent

MonitorAgent 是一个面向主题监控的智能信息采集与摘要 Agent。用户只需要输入一句自然语言主题，系统会自动完成关键词生成、多通道采集、时间过滤、去重、相关性判断、中文摘要和时间线展示。

项目同时提供 Web 实时界面和 Textual 终端界面，适合本地使用，也适合部署到服务器进行公开展示。

## 项目亮点

- Planner 自动拆解主题，生成标签、搜索词、RSS 源和网页源
- 四通道并行采集，降低整体等待时间
- 英文搜索和中文搜索使用 Tavily，兼顾中英文信息源
- RSS 通道支持主流媒体、技术博客和官方博客
- 网页/官方源通道同时支持普通网页和 GitHub 官方仓库
- GitHub 源自动拉取仓库最新 release 和 commit
- 时间过滤支持“最新、最近、近期、近 N 天”等表达
- 五层去重降低重复信息，提升最终结果质量
- 使用二元相关性判断，减少无关结果
- 按批次调用大模型生成 2-3 句中文摘要
- Web 前端支持实时流式状态、通道工具调用展示和时间线排序
- Textual 终端界面支持完整交互流程

## 系统架构

```mermaid
flowchart LR
    A[用户输入主题] --> B[Planner 规划]
    B --> C[四通道并行采集]
    C --> D[时间过滤]
    D --> E[五层去重]
    E --> F[二元相关性判断]
    F --> G[批量中文摘要]
    G --> H[时间线展示]
```

## 核心流水线

1. **Planner**
   - 根据用户主题生成 5-12 个兴趣标签
   - 生成英文和中文搜索查询词
   - 选择相关 RSS 源、网页源和官方 GitHub 仓库
   - 解析时间窗口，例如“最新、最近、近期”

2. **Collector**
   - 使用 LLM function calling 自动调用工具
   - 支持 `search_web`、`fetch_rss`、`fetch_web`、`fetch_github`
   - 四通道并行执行：英文搜索、中文搜索、RSS、网页/官方源

3. **时间过滤**
   - 根据 Planner 识别的时间窗口过滤条目
   - 如果近期条目不足，则保留日期缺失条目，避免结果直接归零

4. **去重**
   - 使用 URL 归一化、标题相似度和内容相似度等策略
   - 对同一事件的多来源报道进行聚合

5. **相关性判断**
   - 将标题、摘要、正文与用户原始主题进行对比
   - 使用二元判断决定保留或丢弃

6. **摘要生成**
   - 按批次调用大模型
   - 每批默认 5 条，降低单次请求压力
   - 输出简洁的中文摘要

7. **时间线**
   - 最终结果按发布时间分组
   - Web 前端在生成摘要时逐步插入并排序

## 技术栈

- Python
- FastAPI
- WebSocket
- HTML / CSS / JavaScript
- Textual
- OpenAI 兼容 LLM API
- Tavily Search API
- GitHub REST API
- feedparser
- trafilatura
- httpx
- rapidfuzz

## 快速开始

### 1. 安装依赖

```powershell
cd monitor-agent
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，填入真实 Key。

### 3. 启动 Web 界面

Windows 一键启动：

```powershell
.\run_web.cmd
```

或者手动启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
```

访问：

```text
http://127.0.0.1:8000
```

### 4. 启动 Textual 界面

```powershell
.\run_monitor.cmd
```

## 服务器部署

以下以 Ubuntu 为例。

### 1. 安装基础环境

```bash
apt update
apt install -y git python3 python3-venv python3-pip
```

### 2. 拉取项目

```bash
cd /opt
git clone https://github.com/acd2113/monitor-agent.git
cd monitor-agent
```

### 3. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
nano .env
```

### 5. 配置 systemd 服务

```bash
cat > /etc/systemd/system/monitor-agent.service <<'EOF'
[Unit]
Description=Monitor Agent Web
After=network.target

[Service]
WorkingDirectory=/opt/monitor-agent
ExecStart=/opt/monitor-agent/.venv/bin/uvicorn src.web.app:app --host 0.0.0.0 --port 8000
Restart=always
User=root
EnvironmentFile=/opt/monitor-agent/.env

[Install]
WantedBy=multi-user.target
EOF
```

启动服务：

```bash
systemctl daemon-reload
systemctl enable --now monitor-agent
systemctl status monitor-agent
```

### 6. 放行端口

```bash
ufw allow 8000/tcp
```

如果使用云服务器，还需要在云平台安全组中放行 TCP `8000` 端口。

部署完成后访问：

```text
http://服务器公网IP:8000
```

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `LLM_API_KEY` | 大模型 API Key |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 模型名称 |
| `LLM_TIMEOUT` | 大模型请求超时时间 |
| `TAVILY_API_KEY` | Tavily 搜索 API Key |
| `GITHUB_API_KEY` | GitHub API Token，可选，用于提升请求额度 |
| `RSS_FEEDS` | 额外 RSS 源，逗号分隔 |
| `SOURCES_FILE` | 信息源配置文件 |
| `KEYWORD_FILTER_FILE` | 可选关键词过滤文件 |
| `MAX_SEARCH_ROUNDS` | 每个通道最大工具调用轮数 |
| `MAX_WEB_SEARCHES` | 单通道最大网页搜索次数 |
| `MAX_RESULTS_PER_SOURCE` | 单次搜索最大结果数 |
| `RELEVANCE_THRESHOLD` | 相关性阈值 |
| `CLASSIFY_BATCH_SIZE` | 相关性和摘要处理批次大小 |
| `REQUEST_TIMEOUT` | 普通网络请求超时时间 |

## 项目结构

```text
monitor-agent/
├── src/
│   ├── agent/                 # 采集 Agent
│   ├── infrastructure/        # LLM 客户端
│   ├── pipeline/              # 规划、过滤、去重、相关性、摘要、时间线
│   ├── sources/               # Tavily、RSS、Web、GitHub 数据源
│   ├── tui/                   # Textual 终端界面
│   ├── web/                   # FastAPI Web 界面
│   ├── config.py
│   ├── models.py
│   └── prompts.py
├── tests/                     # 单元测试
├── docs/                      # 设计和方案文档
├── sources.json               # 可配置信息源
├── requirements.txt
├── run_monitor.cmd
└── run_web.cmd
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

服务器端：

```bash
.venv/bin/python -m pytest -q
```

## 安全说明

- `.env` 已加入 `.gitignore`
- 仓库中只保留 `.env.example`
- 不要提交任何真实 API Key
- GitHub Token 建议使用 `public_repo` 权限，只读取公开仓库
