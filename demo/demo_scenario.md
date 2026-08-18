# SRE 面试 Demo 场景 — 502 故障排查

> **时长**: 5 分钟  \
> **角色**: 面试官观看，候选人操作演示  \
> **目标**: 展示 AI Agent 自动诊断 K8s 故障 + MCP 工具调用 + RAG 知识检索 + 结构化报告输出

---

## 准备工作（演示前完成）

```bash
# 1. 启动项目
docker compose up -d

# 2. 导入 Demo 知识库
python demo/import_demo_data.py

# 3. 打开浏览器
# http://localhost
```

---

## 面试演示步骤

### Step 1: 项目总览（30 秒）

| 操作 | 话术 |
|------|------|
| 打开浏览器，展示 **Executive Dashboard** (`/overview`) | "这是企业级 AI SRE 平台，基于 LangGraph + MCP + RAG 构建。核心能力：让运维人员通过自然语言完成故障诊断。" |
| 指向健康评分、Agent 执行趋势 | "Dashboard 展示系统健康状态、KPI 指标和 Agent 执行趋势。" |

### Step 2: 展示 Knowledge Hub（30 秒）

| 操作 | 话术 |
|------|------|
| 导航到 **Knowledge** (`/knowledge`) | "这是企业知识库，已导入了 K8s 故障手册、Nginx 指南、部署规范三份文档。" |
| 在搜索框输入 "OOMKilled" | "RAG 引擎通过语义检索命中相关章节，为 Agent 提供上下文。" |

### Step 3: 核心 Demo — 502 故障诊断（2 分钟）

| 操作 | 话术 |
|------|------|
| 导航到 **AI Copilot** (`/ops`) | "现在我们模拟一个真实 SRE 场景：生产环境 K8s 集群出现 502。" |
| 输入：`生产支付服务大量502，请帮我分析原因` 并发送 | "Agent 会做什么？它自动分析意图 → 调用工具 → 检索知识库 → 生成报告。" |

**SSE 流式面板展示：**

| 时间 | 面板显示 | Agent 行为 | 面试官解读 |
|------|---------|-----------|-----------|
| 0-3s | 🤔 分析用户需求 → completed | Agent 识别意图：故障诊断 | "LangGraph 的 Agent Node 首先分析用户意图，注入 RAG 和 Memory 上下文。" |
| 3-6s | 🔧 调用 k8s_get_pods → completed | 查询 `namespace=production` 的 Pod 状态 | "调用 MCP 工具 `k8s_get_pods`，返回 CrashLoopBackOff。" |
| 6-9s | 🔧 调用 k8s_logs → completed | 查看 Pod 日志 | "调用 MCP 工具 `k8s_logs`，发现 Java OutOfMemoryError。" |
| 9-12s | 🔧 调用 knowledge_search → completed | RAG 检索 | "调用 `knowledge_search`，检索 K8s 故障手册，命中 OOMKilled 排查 SOP。" |
| 12-15s | 🔧 调用 system_logs → completed | Nginx 日志分析 | "调用系统日志工具，发现 18 条 `connect() failed (111)`。" |
| 15-20s | 📋 AI 生成报告 → completed | LLM 综合推理 | "DeepSeek-V4-Flash 综合所有工具结果和知识库信息，生成结构化 Incident Report。" |

### Step 4: 展示 Incident Report（30 秒）

| 报告部分 | 内容示例 | 面试官解读 |
|---------|---------|-----------|
| **问题摘要** | payment-service 502 Bad Gateway | "Agent 自动总结问题。" |
| **根因分析** | OOMKilled + 连接池耗尽 | "Agent 做了 RCA。" |
| **诊断证据** | K8s 事件 / 日志 / RAG 引用 | "每一步都有证据，可溯源。" |
| **处理方案** | 扩容 + 调整 limits + HPA | "给出可操作的建议。" |
| **优化建议** | PDB / ReadinessProbe / 熔断 | "还提出了长期优化。" |

### Step 5: 展示 Agent Trace（30 秒）

| 操作 | 话术 |
|------|------|
| 导航到 **Traces** (`/traces`) | "完整的 Agent 执行链路 Trace，每一步工具调用的输入、输出、耗时清晰可见。" |
| 点击上一条执行记录查看瀑布时间线 | "这就是 AI 可观测性 — 每一次故障诊断都可追溯、可审计。" |

### Step 6: 展示其他能力（30 秒）

| 页面 | 操作 | 话术 |
|------|------|------|
| **Infrastructure** (`/infra`) | 展示 Docker / K8s / Servers | "多维度基础设施管理。" |
| **Monitor** (`/monitor`) | 展示 Prometheus 指标 + Grafana | "可观测性平台集成。" |

---

## 面试官常见追问与应答

### Q1: "Agent 怎么知道调用哪个工具？"

> "Agent 使用 LangGraph StateGraph 编排。系统给 LLM 注入了工具 Schema（Function Calling 格式），LLM 根据用户意图自主选择工具并生成参数。Agent Node 做推理，Tools Node 执行，循环直到问题解决。"

### Q2: "MCP 协议解决了什么问题？"

> "MCP 解决的是工具标准化问题。如果没有 MCP，每接一个新工具都需要改 Agent 代码。有了 MCP，工具作为独立 Server 暴露标准接口（list_tools / call_tool），Agent 端自动发现和调用，真正实现了工具与 Agent 的解耦。"

### Q3: "RAG 知识库怎么保证数据安全？"

> "v3.3 实现了多租户隔离。Organization 级别的 RBAC：Admin 管理全部，DevOps 使用，Viewer 只读。知识文档按 organization_id 过滤，跨组织完全不可见。Agent 的 knowledge_search 工具也注入了当前用户的 org_id 和 user_id 做过滤。"

### Q4: "这个项目你负责哪些部分？"

> "我是项目的 Tech Lead，负责整体架构设计、Agent 引擎构建、MCP 集成方案、知识库设计。具体实现了 LangGraph 工作流编排、工具注册与路由、RAG 知识库与企业 Hub、SSE 流式输出、Agent Trace 全链路追踪等核心模块。"

### Q5: "遇到的最大技术挑战是什么？"

> "最大的挑战是 Agent Tool Calling 的稳定性。LLM 可能生成格式错误的参数或选择错误的工具。我们通过多层防御来解决：Pydantic Schema 校验、工具执行异常处理、Trace 全链路回溯。另一个挑战是多租户知识隔离，需要保证 RAG 检索和 Agent 工具同时遵守权限边界。"

---

## 故障排查（Demo 现场应急）

| 现象 | 原因 | 快速解决 |
|------|------|---------|
| 前端白屏 | 前端未构建或 Docker 未启动 | `docker compose up -d --build` |
| Agent 不调用工具 | MCP 未连接或 LLM Key 无效 | 检查 `.env` 中 SILICONFLOW_API_KEY |
| 知识库搜索结果为空 | Demo 数据未导入 | `python demo/import_demo_data.py` |
| WebSocket 连接失败 | 后端未启动或端口被占用 | 检查 `python run.py` 或端口 8000 |

---

> **文档版本**: v3.3.0 | **更新日期**: 2026-08-18 | **返回**: [README](../README.md)