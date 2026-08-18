/**
 * Capture README screenshots from the real React console.
 * Usage (from repo root or frontend/):
 *   node scripts/capture_screenshots.mjs
 */
import { spawn } from "node:child_process";
import { mkdir, access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import http from "node:http";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const frontend = path.join(root, "frontend");
const outDir = path.join(root, "screenshots");
const BASE = process.env.SHOT_BASE || "http://127.0.0.1:5174";

const INCIDENT = `# 故障报告

## 事件摘要
生产环境 payment-service 自 09:25（UTC）起出现大量 HTTP 502 Bad Gateway。3 个 Pod 进入 CrashLoopBackOff 后，Nginx 将全部 upstream 标记为不可用。

## 严重级别
严重（Critical）

## 影响范围
- POST /api/payment/charge、refund 接口不可用
- 预计影响 12,000+ 在线用户
- order-service 支付回调积压

## 根因分析
1. JVM 堆内存耗尽（java.lang.OutOfMemoryError）→ OOMKilled（exit 137）
2. HikariCP 连接池打满（100/100），泄漏连接阻塞线程
3. Nginx upstream connect() failed（111: Connection refused）

## 诊断证据
- kubectl_get_pods：payment-service-* 处于 CrashLoopBackOff，重启 5 次
- kubectl_logs：Java heap space + ConnectionPoolTimeout
- knowledge_search：命中 Kubernetes OOMKilled 运维手册
- system_logs：nginx connect() failed × 18

## 建议处理
1. 将 deployment/payment-service 扩容至 5 副本
2. memory limits 由 512Mi 提升至 1Gi
3. 开启 HikariCP leak-detection-threshold=60000

## 预防措施
- 基于内存配置 HPA，PDB minAvailable=2，ReadinessProbe 延迟 60s
`;

const USER = { id: 1, username: "sre-admin", email: "sre@example.com", role: "admin" };

function json(route, data, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(data),
  });
}

function waitHealth(url, timeoutMs = 60000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) return resolve();
        retry();
      });
      req.on("error", retry);
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) return reject(new Error("frontend not ready"));
      setTimeout(tick, 400);
    };
    tick();
  });
}

async function mockApi(page) {
  await page.route("**/health", (route) =>
    json(route, {
      status: "healthy",
      version: "3.3.0",
      environment: "production",
      services: { api: "up", database: "up", llm: "up", monitoring: "up" },
      servers_managed: 8,
    }),
  );

  await page.route((url) => url.pathname.startsWith("/api/"), async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const p = url.pathname.replace(/^\/api/, "") || "/";
    const method = req.method();

    if (p === "/auth/me") return json(route, USER);
    if (p === "/auth/login") {
      return json(route, { access_token: "demo-token", user: USER });
    }

    if (p === "/overview") {
      return json(route, {
        health_score: 87,
        sla_percent: 99.2,
        risk_count: 1,
        executions_24h: 128,
        repair_count: 3,
        time_saved_hours: 12.5,
        health: {
          status: "healthy",
          version: "3.3.0",
          environment: "production",
          services: { api: "up", database: "up", llm: "up", monitoring: "up" },
          servers_managed: 8,
        },
        resources: {
          cpu: { percent: 42, cores: 32 },
          memory: { percent: 61, total_gb: 64, used_gb: 39.1 },
          disks: [{ percent: 48, total_gb: 500, used_gb: 240 }],
        },
        stats: {
          total_conversations: 86,
          total_messages: 412,
          total_servers: 8,
          total_executions: 128,
          success_executions: 121,
          tools_available: 17,
        },
        trend: [
          { day: "08-12", success: 18, failed: 1 },
          { day: "08-13", success: 22, failed: 0 },
          { day: "08-14", success: 19, failed: 2 },
          { day: "08-15", success: 25, failed: 1 },
          { day: "08-16", success: 21, failed: 0 },
          { day: "08-17", success: 24, failed: 1 },
          { day: "08-18", success: 16, failed: 1 },
        ],
        incidents: [
          {
            id: 1,
            level: "critical",
            title: "payment-service 大量 502 Bad Gateway",
            status: "firing",
            created_at: "2026-08-18T09:25:00Z",
          },
        ],
        recent_runs: [
          { id: 41, status: "success", duration: 18.2, tools_called: 4, created_at: "2026-08-18T09:26:00Z" },
          { id: 40, status: "success", duration: 9.4, tools_called: 2, created_at: "2026-08-18T08:11:00Z" },
        ],
      });
    }

    if (p === "/conversations") {
      return json(route, [
        { id: 1, title: "payment-service 502 诊断", updated_at: "2026-08-18T09:26:00Z", message_count: 2 },
      ]);
    }
    if (p === "/conversations/1") {
      return json(route, {
        messages: [
          { role: "user", content: "payment-service 返回大量 502，请分析原因" },
          { role: "assistant", content: INCIDENT },
        ],
      });
    }

    if (p === "/agent/executions") {
      return json(route, [
        { id: 41, conversation_id: 1, status: "success", duration: 18.2, tools_called: 4, created_at: "2026-08-18T09:26:00Z" },
      ]);
    }
    if (p === "/agent/traces/1") {
      return json(route, {
        steps: [
          { event: "user_request", content: "payment-service 返回大量 502，请分析原因", duration: 12 },
          { event: "agent_start", content: "Plan: inspect pods, logs, knowledge, nginx", duration: 80 },
          { event: "rag_search", content: "query=K8s 502 OOMKilled", duration: 140 },
          { event: "tool_call", tool: "kubectl_get_pods", content: "namespace=production", duration: 420 },
          { event: "tool_result", tool: "kubectl_get_pods", content: "CrashLoopBackOff x3", duration: 18 },
          { event: "tool_call", tool: "kubectl_logs", content: "pod=payment-service-7f9c", duration: 510 },
          { event: "tool_result", tool: "kubectl_logs", content: "OutOfMemoryError: Java heap space", duration: 22 },
          { event: "tool_call", tool: "knowledge_search", content: "OOMKilled 连接池", duration: 90 },
          { event: "tool_call", tool: "system_logs", content: "nginx error", duration: 160 },
          { event: "final_answer", content: "Incident Report generated", duration: 640 },
        ],
      });
    }

    if (p === "/knowledge/sources") {
      return json(route, [
        {
          id: 1,
          organization_id: 1,
          type: "feishu",
          name: "生产运维 SOP Wiki",
          status: "connected",
          last_sync_at: "2026-08-18T08:00:00Z",
          last_error: null,
          created_at: "2026-08-01T00:00:00Z",
          upcoming: false,
        },
      ]);
    }
    if (p === "/knowledge/sync/tasks") {
      return json(route, [
        {
          id: 9,
          source_id: 1,
          trigger: "manual",
          status: "success",
          stats: { fetched: 12, ingested: 12 },
          started_at: "2026-08-18T08:00:00Z",
          finished_at: "2026-08-18T08:00:08Z",
          created_at: "2026-08-18T08:00:00Z",
        },
      ]);
    }
    if (p === "/knowledge" && method === "GET") {
      return json(route, [
        { id: 1, title: "Kubernetes 生产运维手册", source: "manual", content_preview: "OOMKilled / CrashLoopBackOff / 502", created_at: "2026-08-18T07:00:00Z" },
        { id: 2, title: "Nginx 故障排查指南", source: "manual", content_preview: "502 Bad Gateway / no live upstreams", created_at: "2026-08-18T07:01:00Z" },
        { id: 3, title: "生产部署规范与最佳实践", source: "manual", content_preview: "HPA / ReadinessProbe / 连接池", created_at: "2026-08-18T07:02:00Z" },
      ]);
    }
    if (p === "/knowledge/search" && method === "POST") {
      return json(route, [
        { title: "Kubernetes 生产运维手册", source: "manual", score: 0.91, content: "OOMKilled: 提高 memory limits，检查 JVM heap 与泄漏。" },
        { title: "Nginx 故障排查指南", source: "manual", score: 0.84, content: "502 常见于 upstream Connection refused，结合 Pod 就绪探针。" },
      ]);
    }

    if (p === "/servers") {
      return json(route, [
        { id: 1, name: "prod-k8s-node-a", host: "10.0.1.11", port: 22, username: "ops", auth_type: "key", description: "production node A", is_active: true, created_at: "2026-08-01T00:00:00Z", updated_at: "2026-08-18T00:00:00Z" },
        { id: 2, name: "prod-k8s-node-b", host: "10.0.1.12", port: 22, username: "ops", auth_type: "key", description: "production node B", is_active: true, created_at: "2026-08-01T00:00:00Z", updated_at: "2026-08-18T00:00:00Z" },
      ]);
    }
    if (p === "/k8s/pods") {
      return json(route, {
        pods: [
          { namespace: "production", name: "payment-service-7f9c-aaa", status: "CrashLoopBackOff", ready: "0/1", restarts: 5 },
          { namespace: "production", name: "payment-service-7f9c-bbb", status: "CrashLoopBackOff", ready: "0/1", restarts: 5 },
          { namespace: "production", name: "payment-service-7f9c-ccc", status: "CrashLoopBackOff", ready: "0/1", restarts: 4 },
          { namespace: "production", name: "nginx-ingress-controller-x", status: "Running", ready: "1/1", restarts: 0 },
        ],
      });
    }
    if (p === "/k8s/nodes") {
      return json(route, {
        nodes: [
          { name: "prod-cpu-a", status: "Ready", role: "worker", cpu: "32", memory: "64Gi", kubelet_version: "v1.28.4" },
          { name: "prod-cpu-b", status: "Ready", role: "worker", cpu: "32", memory: "64Gi", kubelet_version: "v1.28.4" },
        ],
      });
    }

    if (p === "/alerts") return json(route, [{ id: 1, level: "critical", title: "High5xxRate payment-service", status: "firing" }]);
    if (p === "/agent/stats") {
      return json(route, {
        total_conversations: 86,
        total_messages: 412,
        total_servers: 8,
        total_executions: 128,
        success_executions: 121,
        tools_available: 17,
      });
    }
    if (p === "/server/status") {
      return json(route, {
        cpu: { percent: 42, cores: 32 },
        memory: { percent: 61, total_gb: 64, used_gb: 39.1 },
        disks: [{ percent: 48, total_gb: 500, used_gb: 240 }],
      });
    }

    if (p === "/chat/stream" && method === "POST") {
      const events = [
        { type: "agent_start", content: "规划：查 Pod / 日志 / 知识库 / Nginx" },
        { type: "rag_search", status: "completed", result_count: 3 },
        { type: "tool_call", tool: "kubectl_get_pods", status: "running" },
        { type: "tool_result", tool: "kubectl_get_pods", status: "completed" },
        { type: "tool_call", tool: "kubectl_logs", status: "running" },
        { type: "tool_result", tool: "kubectl_logs", status: "completed" },
        { type: "tool_call", tool: "knowledge_search", status: "running" },
        { type: "tool_result", tool: "knowledge_search", status: "completed" },
        { type: "tool_call", tool: "system_logs", status: "running" },
        { type: "tool_result", tool: "system_logs", status: "completed" },
        { type: "final_answer", content: INCIDENT, report: INCIDENT },
        { type: "complete", report: INCIDENT, conversation_id: 1 },
      ];
      const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
      return route.fulfill({ status: 200, contentType: "text/event-stream", body });
    }

    return json(route, {});
  });
}

async function shot(page, file, extraWait = 800) {
  await page.waitForTimeout(extraWait);
  await page.screenshot({ path: path.join(outDir, file), fullPage: false });
  console.log("wrote", file);
}

async function main() {
  await mkdir(outDir, { recursive: true });
  try {
    await access(path.join(frontend, "node_modules"));
  } catch {
    console.error("Run npm install in frontend/ first");
    process.exit(1);
  }
  const require = createRequire(path.join(frontend, "package.json"));
  let chromium;
  try {
    ({ chromium } = require("playwright"));
  } catch {
    console.error("Install Playwright in frontend/: npm install playwright --no-save && npx playwright install chromium");
    process.exit(1);
  }

  const vite = spawn("npx", ["vite", "--port", "5174", "--strictPort", "--host", "127.0.0.1"], {
    cwd: frontend,
    shell: true,
    stdio: "pipe",
    env: { ...process.env, BROWSER: "none" },
  });
  vite.stdout.on("data", (d) => process.stdout.write(d));
  vite.stderr.on("data", (d) => process.stderr.write(d));

  try {
    await waitHealth(BASE);
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.addInitScript((user) => {
      localStorage.setItem("access_token", "demo-token");
      localStorage.setItem("user", JSON.stringify(user));
      localStorage.setItem("sre-locale", "zh");
      localStorage.setItem("sre-theme", "night");
    }, USER);
    await mockApi(page);

    const only = process.env.SHOT_ONLY || "";

    if (!only) {
    await page.goto(`${BASE}/overview`, { waitUntil: "networkidle" });
    try {
      await page.waitForSelector("text=/当前风险|Risk|health|健康/i", { timeout: 20000 });
    } catch (e) {
      await page.screenshot({ path: path.join(outDir, "_debug.png"), fullPage: true });
      console.log("debug url", page.url());
      console.log("debug html snippet", (await page.content()).slice(0, 1200));
      throw e;
    }
    await shot(page, "01-dashboard.png", 1200);
    }

    await page.goto(`${BASE}/ops`, { waitUntil: "networkidle" });
    await page.getByPlaceholder(/输入运维问题/).fill("payment-service 返回大量 502，请分析原因");
    await page.getByRole("button", { name: "发送" }).click();
    await page.getByText("故障报告", { timeout: 15000 }).waitFor();
    await shot(page, "02-agent-chat.png", 800);

    if (only === "chat") {
      await browser.close();
      return;
    }

    await page.evaluate(() => {
      const nodes = [...document.querySelectorAll("h1, h2, p, div")];
      const hit = nodes.find((n) => n.textContent?.includes("事件摘要"));
      hit?.scrollIntoView({ block: "start" });
    });
    await shot(page, "06-incident-report.png", 400);

    await page.goto(`${BASE}/knowledge`, { waitUntil: "networkidle" });
    await page.getByText("生产运维 SOP Wiki", { timeout: 10000 }).waitFor();
    await shot(page, "03-knowledge-hub.png", 600);

    await page.goto(`${BASE}/traces?cid=1`, { waitUntil: "networkidle" });
    await page.getByText("kubectl_get_pods").first().waitFor({ timeout: 10000 });
    await shot(page, "04-trace-viewer.png", 600);

    await page.goto(`${BASE}/infra`, { waitUntil: "networkidle" });
    await page.getByRole("button", { name: "Kubernetes" }).click();
    await page.getByText("payment-service-7f9c-aaa", { timeout: 10000 }).waitFor();
    await shot(page, "05-kubernetes.png", 800);

    const arch = path.join(root, "scripts", "architecture.html");
    const archPage = await browser.newPage({
      viewport: { width: 1600, height: 1200 },
      deviceScaleFactor: 2,
    });
    await archPage.goto(pathToFileURL(arch).href, { waitUntil: "networkidle" });
    await archPage.locator(".mermaid svg").first().waitFor({ timeout: 20000 });
    await archPage.waitForTimeout(800);
    await archPage.locator("#capture").screenshot({
      path: path.join(outDir, "07-architecture.png"),
      type: "png",
    });
    await archPage.close();
    console.log("wrote", "07-architecture.png");

    await browser.close();
  } finally {
    vite.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
