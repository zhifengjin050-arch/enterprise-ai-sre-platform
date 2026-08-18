/**
 * AI 智能运维助手 — 前端逻辑
 *
 * 功能：
 * - Session 管理（localStorage）
 * - 聊天消息发送（POST /api/chat）
 * - Markdown 渲染（marked.js）
 * - 代码高亮（highlight.js）
 * - 服务器状态仪表盘自动刷新（30s）
 * - Agent 执行轨迹展示（可折叠）
 */

// ============================================================
// Session 管理
// ============================================================
function getSessionId() {
  let id = localStorage.getItem("devops_session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("devops_session_id", id);
  }
  return id;
}

// ============================================================
// Marked.js 配置
// ============================================================
marked.setOptions({
  breaks: true,
  gfm: true,
});

// ============================================================
// DOM 引用
// ============================================================
const messagesContainer = document.getElementById("chat-messages");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const traceToggle = document.getElementById("trace-toggle");
const traceBody = document.getElementById("trace-body");
const traceSteps = document.getElementById("trace-steps");
const traceStatus = document.getElementById("trace-status");

// Dashboard 元素
const cpuBar = document.getElementById("cpu-bar");
const cpuValue = document.getElementById("cpu-value");
const memBar = document.getElementById("mem-bar");
const memValue = document.getElementById("mem-value");
const diskBar = document.getElementById("disk-bar");
const diskValue = document.getElementById("disk-value");

// ============================================================
// 服务器状态仪表盘 — 每 30 秒自动刷新
// ============================================================
async function fetchServerStatus() {
  try {
    const res = await fetch("/api/server/status");
    if (!res.ok) return;
    const data = await res.json();

    const cpu = data.cpu?.percent ?? 0;
    const mem = data.memory?.percent ?? 0;
    const diskPct = data.disks?.[0]?.percent ?? 0;

    cpuBar.style.width = cpu + "%";
    cpuValue.textContent = cpu + "%";

    memBar.style.width = mem + "%";
    memValue.textContent = mem + "%";

    diskBar.style.width = diskPct + "%";
    diskValue.textContent = diskPct + "%";

    // 根据使用率调整进度条颜色
    updateBarColor(cpuBar, cpu);
    updateBarColor(memBar, mem);
    updateBarColor(diskBar, diskPct);
  } catch (err) {
    console.warn("获取服务器状态失败:", err);
  }
}

function updateBarColor(bar, percent) {
  if (percent > 90) {
    bar.style.background = "linear-gradient(90deg, #ef4444, #dc2626)";
  } else if (percent > 80) {
    bar.style.background = "linear-gradient(90deg, #f59e0b, #f97316)";
  } else if (percent > 70) {
    bar.style.background = "linear-gradient(90deg, #f59e0b, #eab308)";
  }
  // otherwise keep the CSS default gradient
}

// 立即获取一次，之后每 30 秒刷新
fetchServerStatus();
setInterval(fetchServerStatus, 30000);

// ============================================================
// Agent 执行轨迹 — 可折叠面板
// ============================================================
let traceOpen = false;

traceToggle.addEventListener("click", () => {
  traceOpen = !traceOpen;
  traceToggle.classList.toggle("trace-header--open", traceOpen);
  traceBody.classList.toggle("trace-body--open", traceOpen);
});

function renderTrace(steps) {
  traceSteps.innerHTML = "";
  traceStatus.textContent = "";

  if (!steps || steps.length === 0) return;

  // 检查是否全部完成
  const allDone = steps.every((s) => s.status === "completed");
  traceStatus.textContent = allDone ? "执行完成" : "";

  // 自动展开
  if (!traceOpen) {
    traceToggle.click();
  }

  steps.forEach((s) => {
    const div = document.createElement("div");
    div.className = "trace-step";

    if (s.status === "completed") div.classList.add("trace-step--completed");
    else if (s.status === "running") div.classList.add("trace-step--running");
    else if (s.status === "failed") div.classList.add("trace-step--failed");

    const icon = document.createElement("span");
    icon.className = "trace-step-icon";
    div.appendChild(icon);

    const label = document.createElement("span");
    label.className = "trace-step-label";
    label.textContent = s.step;
    div.appendChild(label);

    if (s.duration_ms > 0) {
      const dur = document.createElement("span");
      dur.className = "trace-step-duration";
      dur.textContent = formatDuration(s.duration_ms);
      div.appendChild(dur);
    }

    traceSteps.appendChild(div);
  });
}

function formatDuration(ms) {
  if (ms < 1000) return ms.toFixed(0) + "ms";
  return (ms / 1000).toFixed(1) + "s";
}

// ============================================================
// 消息渲染
// ============================================================
function createMessageElement(role, content) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", `message--${role}`);

  if (role === "ai") {
    const card = document.createElement("div");
    card.classList.add("message-card", "glass");

    const header = document.createElement("div");
    header.classList.add("message-header");
    header.innerHTML = `
      <span class="message-avatar">AI</span>
      <span class="message-sender">AI 智能运维助手</span>
    `;

    const body = document.createElement("div");
    body.classList.add("message-body");
    body.innerHTML = marked.parse(content);

    body.querySelectorAll("pre code").forEach((block) => {
      hljs.highlightElement(block);
    });

    card.appendChild(header);
    card.appendChild(body);
    messageDiv.appendChild(card);
  } else {
    const card = document.createElement("div");
    card.classList.add("message-card");

    const body = document.createElement("div");
    body.classList.add("message-body");
    body.textContent = content;

    card.appendChild(body);
    messageDiv.appendChild(card);
  }

  return messageDiv;
}

function createLoadingElement() {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message", "message--ai", "message--loading");
  messageDiv.id = "loading-message";

  const card = document.createElement("div");
  card.classList.add("message-card", "glass");

  const header = document.createElement("div");
  header.classList.add("message-header");
  header.innerHTML = `
    <span class="message-avatar">AI</span>
    <span class="message-sender">AI 正在分析...</span>
  `;

  const loadingDots = document.createElement("div");
  loadingDots.classList.add("loading-dots");
  loadingDots.innerHTML = "<span></span><span></span><span></span>";

  card.appendChild(header);
  card.appendChild(loadingDots);
  messageDiv.appendChild(card);

  return messageDiv;
}

function removeLoading() {
  const loadingMsg = document.getElementById("loading-message");
  if (loadingMsg) loadingMsg.remove();
}

function addMessage(role, content) {
  const msg = createMessageElement(role, content);
  messagesContainer.appendChild(msg);
  scrollToBottom();
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================================
// API 通信
// ============================================================
async function sendMessage(message) {
  // 显示加载中
  const loadingEl = createLoadingElement();
  messagesContainer.appendChild(loadingEl);
  scrollToBottom();

  setInputEnabled(false);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        session_id: getSessionId(),
      }),
    });

    if (!response.ok) {
      throw new Error("服务器错误: " + response.status);
    }

    const data = await response.json();

    // 渲染 Agent 执行轨迹
    if (data.trace && data.trace.length > 0) {
      renderTrace(data.trace);
    }

    return data.report || "Agent 返回为空。";

  } catch (error) {
    console.error("聊天 API 错误:", error);
    return "**请求失败**\n\n无法连接到 AI 智能运维助手，请检查服务器是否正在运行。";
  } finally {
    removeLoading();
    setInputEnabled(true);
    userInput.focus();
  }
}

function setInputEnabled(enabled) {
  userInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
}

// ============================================================
// 事件处理
// ============================================================
function handleSend() {
  const text = userInput.value.trim();
  if (!text) return;

  addMessage("user", text);
  userInput.value = "";
  userInput.style.height = "auto";

  sendMessage(text).then((reply) => {
    addMessage("ai", reply);
  });
}

sendBtn.addEventListener("click", handleSend);

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
});

// ============================================================
// 初始化
// ============================================================
function init() {
  // 添加中文欢迎消息
  const welcomeDiv = document.createElement("div");
  welcomeDiv.classList.add("message", "message--ai", "slide-up");
  welcomeDiv.innerHTML = `
    <div class="message-card glass">
      <div class="message-header">
        <span class="message-avatar">AI</span>
        <span class="message-sender">AI 智能运维助手</span>
      </div>
      <div class="message-body">
        <p>欢迎使用 <strong>AI 智能运维助手</strong>。</p>
        <p>我是您的企业级 AI 运维 Agent，支持以下能力：</p>
        <ul>
          <li>✓ 服务器状态检测 — CPU、内存、磁盘实时监控</li>
          <li>✓ Docker 容器分析 — 查看容器状态与日志</li>
          <li>✓ 系统日志分析 — 查询系统错误日志</li>
          <li>✓ Kubernetes 管理 — 查看 Pod、Deployment、Service</li>
          <li>✓ 自动故障诊断 — 发现异常自动分析根因</li>
        </ul>
        <p class="message-hint">💡 输入运维问题，我会自动调用工具获取真实数据并生成诊断报告。</p>
      </div>
    </div>
  `;
  messagesContainer.appendChild(welcomeDiv);

  userInput.focus();
  console.log("AI 智能运维助手 UI 初始化完成 — Session:", getSessionId());
}

document.addEventListener("DOMContentLoaded", init);