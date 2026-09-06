const form = document.getElementById("monitor-form");
const topicInput = document.getElementById("topic-input");
const currentTopic = document.getElementById("current-topic");
const statusBox = document.getElementById("status");
const planInfo = document.getElementById("plan-info");
const channelGrid = document.getElementById("channel-grid");
const resultCount = document.getElementById("result-count");
const resultBody = document.querySelector("#results tbody");

const CACHE_KEY = "monitor-agent-last-run-v1";

const channelNames = {
  en_search: "英文搜索",
  zh_search: "中文搜索",
  rss: "RSS 源",
  web: "网页/官方源",
};

let channelCounts = {};
let liveItems = [];
let socket = null;
let lastStatusText = "等待输入主题";
let runStartTime = null;
let elapsedTimer = null;

function ensureSocket() {
  if (socket && socket.readyState === WebSocket.OPEN) return socket;

  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${location.host}/ws`);

  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    handleMessage(message);
  });

  socket.addEventListener("close", () => {
    socket = null;
    stopElapsedTimer();
    setStatus("连接已断开，正在尝试重连...");
    setTimeout(ensureSocket, 1500);
  });

  return socket;
}

function handleMessage(message) {
  if (message.type === "status") {
    setStatus(message.text);
  } else if (message.type === "plan") {
    renderPlan(message.data);
  } else if (message.type === "channel") {
    pushChannelEvent(message.channel_id, message.kind, message.text);
  } else if (message.type === "item_result") {
    addLiveItem(message.data);
  } else if (message.type === "result") {
    renderResult(message.data);
  } else if (message.type === "error") {
    stopElapsedTimer();
    setStatus(`运行失败：${message.text}`);
  }
}

function startElapsedTimer() {
  stopElapsedTimer();
  runStartTime = Date.now();
  elapsedTimer = setInterval(() => {
    statusBox.textContent = statusDisplay();
  }, 1000);
}

function stopElapsedTimer() {
  if (elapsedTimer !== null) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
  runStartTime = null;
}

function elapsedSeconds() {
  if (runStartTime === null) return 0;
  return Math.max(1, Math.round((Date.now() - runStartTime) / 1000));
}

function statusDisplay() {
  if (runStartTime !== null) {
    return `${lastStatusText} · ${elapsedSeconds()}s`;
  }
  return lastStatusText;
}

function setStatus(text) {
  lastStatusText = text;
  statusBox.textContent = statusDisplay();
}

function renderPlan(plan) {
  const tags = (plan.tags || []).map((tag) => tag.tag).join("、") || "无";
  const rssSources = (plan.rss_urls || []).map(hostname).join("\n- ") || "- 无";
  const webSources = (plan.web_urls || []).map(hostname).join("\n- ") || "- 无";
  planInfo.textContent = [
    `标签：${tags}`,
    `关键词：${(plan.keywords || []).join(", ") || "无"}`,
    `英文查询：${(plan.english_queries || []).join(", ") || "无"}`,
    `中文查询：${(plan.chinese_queries || []).join(", ") || "无"}`,
    `RSS 源：\n- ${rssSources}`,
    `网页源：\n- ${webSources}`,
    `时间窗口：${plan.max_age_days || "不限"}`,
  ].join("\n");
}

function hostname(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function getOrCreateChannelCard(channelId) {
  let card = document.getElementById(`channel-${channelId}`);
  if (card) return card;

  card = document.createElement("article");
  card.className = "channel-card";
  card.id = `channel-${channelId}`;
  card.innerHTML = `
    <div class="channel-inner">
      <div class="channel-face front">
        <div class="channel-head">
          <button class="channel-flip" type="button" aria-label="翻转">⇄</button>
          <span class="channel-title">${channelNames[channelId] || channelId}</span>
          <span class="channel-status"><span class="spinner"></span>运行中</span>
        </div>
        <div class="channel-log"></div>
      </div>
      <div class="channel-face back">
        <div class="channel-head">
          <button class="channel-flip" type="button" aria-label="翻转">⇄</button>
          <span class="channel-title">${channelNames[channelId] || channelId}</span>
          <span class="channel-status">获取信息</span>
        </div>
        <div class="channel-items"></div>
      </div>
    </div>
  `;
  channelGrid.appendChild(card);
  channelCounts[channelId] = 0;

  card.querySelectorAll(".channel-flip").forEach((button) => {
    button.addEventListener("click", () => {
      card.classList.toggle("flipped");
    });
  });

  return card;
}

function setChannelStatus(card, text) {
  card.querySelectorAll(".channel-status").forEach((status) => {
    status.textContent = text;
  });
}

function pushChannelEvent(channelId, kind, text) {
  const card = getOrCreateChannelCard(channelId);
  const frontLog = card.querySelector(".channel-log");
  const backItems = card.querySelector(".channel-items");

  if (kind === "item") {
    channelCounts[channelId] = (channelCounts[channelId] || 0) + 1;
    backItems.textContent += `${channelCounts[channelId]}. ${text}\n`;
    setChannelStatus(card, `已获取 ${channelCounts[channelId]} 条`);
  } else if (kind === "tool") {
    frontLog.textContent += `${text}\n`;
  } else if (kind === "error") {
    frontLog.textContent += `错误：${text}\n`;
    setChannelStatus(card, `【共${channelCounts[channelId] || 0}条】错误`);
  } else if (kind === "done") {
    setChannelStatus(card, `【共${channelCounts[channelId] || 0}条】完成`);
    card.classList.add("flipped");
  }

  frontLog.scrollTop = frontLog.scrollHeight;
  backItems.scrollTop = backItems.scrollHeight;
}

function finalizeChannelCards() {
  document.querySelectorAll(".channel-card").forEach((card) => {
    const channelId = card.id.replace("channel-", "");
    setChannelStatus(card, `【共${channelCounts[channelId] || 0}条】完成`);
    card.classList.add("flipped");
  });
}

function appendRow(item) {
  const row = document.createElement("tr");
  const time = document.createElement("td");
  time.textContent = item.published_at
    ? item.published_at.replace("T", " ").slice(0, 16)
    : "";
  const source = document.createElement("td");
  source.textContent = item.source || "";
  const title = document.createElement("td");
  const link = document.createElement("a");
  link.href = item.url || "#";
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = item.title || "";
  title.appendChild(link);
  const summary = document.createElement("td");
  summary.textContent = item.summary_zh || item.snippet || "";
  row.append(time, source, title, summary);
  return row;
}

function renderTimeline(groups) {
  resultBody.innerHTML = "";
  let total = 0;
  for (const group of groups || []) {
    for (const item of group.items || []) {
      total += 1;
      resultBody.appendChild(appendRow(item));
    }
  }
  resultCount.textContent = `${total} 条`;
  return total;
}

function renderResult(data) {
  const total = renderTimeline(data.timeline);
  stopElapsedTimer();
  setStatus(`完成，共 ${total} 条`);
  finalizeChannelCards();
  saveCache(data.timeline);
}

function saveCache(timeline) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      topic: currentTopic.textContent,
      status: lastStatusText,
      plan: planInfo.textContent,
      timeline,
    }));
  } catch {
    // ignore storage errors
  }
}

function loadCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return;
    const cache = JSON.parse(raw);
    if (cache.topic) currentTopic.textContent = cache.topic;
    if (cache.status) setStatus(cache.status);
    if (cache.plan) planInfo.textContent = cache.plan;
    if (cache.timeline) renderTimeline(cache.timeline);
  } catch {
    // ignore malformed cache
  }
}

function renderLiveItems() {
  sortLiveItems();
  resultBody.innerHTML = "";
  liveItems.forEach((item) => resultBody.appendChild(appendRow(item)));
  resultCount.textContent = `${liveItems.length} 条`;
}

function sortLiveItems() {
  liveItems.sort((a, b) => {
    const at = a.published_at ? new Date(a.published_at).getTime() : 0;
    const bt = b.published_at ? new Date(b.published_at).getTime() : 0;
    if (at && bt) return bt - at;
    if (at) return -1;
    if (bt) return 1;
    return 0;
  });
}

function addLiveItem(item) {
  const exists = liveItems.some((existing) => existing.url && existing.url === item.url);
  if (exists) return;
  liveItems.push(item);
  renderLiveItems();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) return;

  currentTopic.textContent = topic;
  planInfo.textContent = "正在规划...";
  resultBody.innerHTML = "";
  channelGrid.innerHTML = "";
  channelCounts = {};
  liveItems = [];
  resultCount.textContent = "0 条";
  setStatus("开始运行...");
  startElapsedTimer();

  const ws = ensureSocket();
  const send = () => {
    ws.send(JSON.stringify({ type: "start", topic }));
  };

  if (ws.readyState === WebSocket.OPEN) {
    send();
  } else {
    ws.addEventListener("open", send, { once: true });
  }

  topicInput.value = "";
});

topicInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    form.dispatchEvent(new Event("submit", { cancelable: true }));
  }
});

loadCache();
topicInput.focus();
