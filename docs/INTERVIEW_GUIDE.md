# 项目面试指南 — Enterprise AI SRE Autonomous Operations Platform

> **适用岗位**: SRE / DevOps Engineer / AI Infra Engineer / Platform Engineer  
> **版本**: v3.3.0 Enterprise Knowledge Hub  
> **准备时间**: 15 分钟

---

## 1. 项目介绍（30 秒 Elevator Pitch）

> "这是一个 **基于 LangGraph + MCP + RAG 的企业级 AI SRE 平台**。核心思路是把 SRE 日常的故障诊断、工具操作、知识检索全部交给 AI Agent 自动完成。运维人员只需要说一句自然语言——比如 '生产环境支付服务出 502 了'——Agent 就会自动调用 Kubernetes 工具检查 Pod、分析日志、从知识库检索故障手册，最后生成一份完整的 Incident Report。整个过程从传统人工排查的 30 分钟缩短到 20 秒。"

### 一句话版本

> **"AI SRE Agent 平台 — 让运维人员用自然语言完成故障诊断，自动调工具 + 查知识库 + 生成报告。"**

---

## 2. 技术架构介绍（2 分钟）

### 整体架构

```
用户 (Browser)
    ↓ HTTP / SSE / WebSocket
FastAPI (47+ 路由端点)
    ↓
LangGraph Agent (StateGraph)
    ├── Agent Node: LLM 推理 + RAG 注入 + Memory 注入
    └── Tools Node: 工具执行 + Trace 记录
    ↓
Tool Router → 内置工具 (18) / MCP 工具 (17)
    ↓
Kubernetes / Docker / SSH / 知识库
```

### 关键技术选型

| 组件 | 选型 | 为什么 |
|------|------|--------|
| **Agent 编排** | LangGraph StateGraph | 比 LangChain AgentExecutor 更灵活，可精确控制状态流转和条件分支 |
| **工具协议** | MCP (Model Context Protocol) | 标准化工具接口，新工具无需改 Agent 代码，动态发现 |
| **知识检索** | RAG (pgvector) | 企业知识实时更新、可解释、可私有化部署，无需微调 |
| **LLM 推理** | DeepSeek-V4-Flash (Function Calling) | 高性能 Tool Calling，支持多轮工具调用 |
| **流式输出** | SSE (Server-Sent Events) | 实时展示 Agent 推理过程，提升交互体验 |
| **可观测性** | Agent Trace + Prometheus + Grafana | 全链路追踪 + 业务指标 + 可视化面板 |

### 回答示例

> "架构上分为四层：接入层（FastAPI + JWT 认证）、编排层（LangGraph StateGraph）、工具层（内置 18 工具 + MCP 17 工具）、知识层（RAG pgvector + 企业知识 Hub）。\n\n核心设计是 LangGraph 的状态图——Agent Node 做推理和规划，Tools Node 执行工具，两者通过条件边循环，直到工具调用完成为止。每次循环都会注入 RAG 上下文和 Memory 上下文，让 LLM 感知企业知识和历史记录。\n\nMCP 协议是亮点——它让工具扩展变成了动态发现。新运维工具只要实现 MCP Server 协议，平台就能自动识别和调用，不需要改任何 Agent 代码。\n\nv3.3 新增的企业知识 Hub 实现了多租户隔离——不同 Organization 的知识完全隔离，凭据加密存储，同步 Pipeline 自动从飞书拉取文档。"

---

## 3. Agent 流程详解

### LangGraph StateGraph 流程

```python
# graph.py — 简洁稳定的状态图
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)   # LLM 推理 + 上下文注入
workflow.add_node("tools", tools_node)   # 工具执行

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,            # 条件边: 有 tool_calls → tools, 否则 → END
    {"tools": "tools", "end": END},
)
workflow.add_edge("tools", "agent")

app = workflow.compile()
```

### 一次完整的 Agent 执行流程

| 步骤 | 节点 | 操作 | 注入内容 |
|------|------|------|---------|
| 1 | **agent** | 分析用户意图 | 系统提示词 |
| 2 | **agent** | LLM 推理（首次） | RAG 知识库上下文 + Memory 历史记录 |
| 3 | **agent** | 返回 tool_calls: [`kubectl_get_pods`, ...] | — |
| 4 | **tools** | 并行执行工具调用 | — |
| 5 | **tools** | 记录 Trace + 推送 SSE 事件 | — |
| 6 | **agent** | LLM 推理（二次） | 工具结果 + 知识库 + 历史 |
| 7 | **agent** | 返回 tool_calls 或直接回答 | — |
| 8 | 循环至无 tool_calls | — | — |
| 9 | **agent** | 输出 final_report | — |

### 回答示例

> "Agent 流程基于 LangGraph 的 StateGraph。Agent Node 每次被调用时，先注入 RAG 知识库检索结果和 Memory 历史记录，然后调用 LLM。LLM 看到当前的 context 和可用工具列表，决定是调用工具还是直接回答。\n\n如果需要工具，生成 tool_calls → 进入 Tools Node 执行 → 结果追加到状态 → 回到 Agent Node 继续推理。这个循环一直到 LLM 认为信息足够，生成最终报告。\n\n关键设计是条件边 `should_continue`——根据 state 中是否有未执行的 tool_calls 决定流向。这样 Agent 可以自由决定需要调用多少次工具，不受硬编码限制。\n\nSSE 流式输出贯穿整个过程——前端实时展示 Agent 的每一步：分析中、检索知识库、调用工具、生成报告。面试官看到这个效果会非常 impressed。"

---

## 4. MCP 协议为什么设计

### 核心问题

传统 Agent 工具扩展方式：每次加新工具需要改 Agent 代码、写新函数、注册新 schema。

### MCP 解决方式

```bash
# MCP Server 独立部署，通过 stdio 通信
Agent → Tool Router → MCP Client → stdio → MCP Server
                                              ├── list_tools() → 返回工具列表
                                              └── call_tool(name, args) → 执行工具
```

### MCP 三大优势

| 优势 | 说明 | 面试价值 |
|------|------|---------|
| **动态发现** | Agent 启动时自动 list_tools，新工具即加即用 | "体现了对工具扩展性的前瞻设计" |
| **协议标准化** | 任何 MCP Server 都可接入 | "不只是 K8s/Docker，未来可接任意企业工具" |
| **进程隔离** | MCP Server 独立进程，崩溃不影响 Agent | "生产环境稳定性保障" |

### 对比：MCP vs 传统集成

| 维度 | 传统内置工具 | MCP 协议 |
|------|------------|---------|
| 扩展方式 | 写代码 + 注册 | 实现 MCP Server |
| 发现机制 | 代码硬编码 | 运行时自动发现 |
| 隔离性 | 同一进程 | 独立子进程 (stdio) |
| 语言 | 仅 Python | 任意语言 |
| 热更新 | 需重启 | 运行时刷新 |

### 回答示例

> "MCP 解决的问题是**工具扩展的解耦**。传统 Agent 加一个新工具需要改代码、注册 schema、测试、部署。而在 MCP 体系下，工具作为一个独立的 Server 运行，通过标准化的 stdio 协议与 Agent 通信。Agent 自动调用 list_tools 发现所有可用工具，不需要预知工具的存在。\n\n这带来了三个好处：第一，工具可以用任意语言实现（Go/Rust/Java），不限于 Python；第二，工具进程独立，crash 不影响 Agent；第三，工具可以热更新，Agent 下次对话自动感知变化。\n\n项目中我们有一个独立的 Enterprise DevOps MCP Server（项目2），提供了 17 个企业运维工具。当 ENABLE_MCP=true 时，Agent 自动连接并合并工具列表；关闭时只使用内置的 18 个工具，完全透明。"

---

## 5. RAG 为什么设计

### 为什么不是微调

```
微调 (Fine-tuning):
  优点: 模型学习新知识
  缺点: 成本高(GPU) / 更新慢(重新训练) / 灾难性遗忘

RAG:
  优点: 实时更新 / 成本低(仅 Embedding) / 可解释 / 私有化
  缺点: 依赖检索质量
```

### RAG 架构

```
文档上传 → Chunk 切分 (chunk_size=500, overlap=50)
         → Embedding API → pgvector (余弦相似度索引)

用户查询 → Embedding → 语义检索 (top_k=3)
         → 结果注入 Agent System Prompt
         → LLM 基于上下文生成回答
```

### v3.3 Knowledge Hub 多租户设计

```
Organization A                     Organization B
  ├── 手动文档 (documents 表)         ├── 手动文档 (documents 表)
  ├── Hub 文档 (knowledge_documents)  ├── Hub 文档 (knowledge_documents)
  └── 知识源 (Feishu 连接器)            └── 知识源 (GitLab Wiki 连接器)
         ✗ 不可见                            ✗ 不可见

Agent knowledge_search
  → 自动过滤 organization_id + user_id
  → 仅返回当前用户可见的文档
```

### 回答示例

> "选择 RAG 而不是微调，核心原因有三个：\n\n**第一，更新频率**。运维文档每周都可能更新——SOP 变更、新服务器上线、架构调整。如果用微调，每次都要重新训练模型，成本高、周期长。RAG 只需要上传文档，立即生效。\n\n**第二，可解释性**。SRE 场景对可信度要求极高——Agent 的建议必须有依据。RAG 可以让 LLM 引用知识库的具体段落，运维人员可以溯源核实。\n\n**第三，成本和安全**。RAG 只需要 Embedding API 调用，不需要 GPU 训练。而且企业知识可以私有化部署，不会泄露到模型训练数据中。\n\nv3.3 新增了企业知识 Hub，实现了多租户隔离。每个 Organization 的知识完全独立——A 公司的故障手册对 B 公司完全不可见。外部知识源（飞书 Wiki）通过 Pipeline 自动同步，凭据用 Fernet 加密存储。Agent 的 knowledge_search 工具自动按 organization_id + user_id 过滤，确保数据安全。"

---

## 6. 面试高频追问

### Q1: "Agent 调用 LLM 时上下文窗口不够怎么办？"

> "我们做了几层优化：\n1. **RAG top_k=3**：只检索最相关的 3 个片段，每个约 400 字\n2. **Memory 限制**：只加载最近 30 天的故障记录，最多 3 条\n3. **Trace 截断**：工具结果在 trace 中只保留前 300 字符\n4. **System Prompt 精简**：提示词控制在 1500 字以内\n5. 如果超长内容（如知识库文档全文），使用 `knowledge_search` 工具按需检索，而非预注入"

### Q2: "工具调用结果不准确怎么办？"

> "我们做了多层防御：\n1. **Schema 校验**：每个工具的参数用 Pydantic 严格校验\n2. **异常处理**：工具执行异常捕获后返回友好错误提示\n3. **Trace 回溯**：每一步工具调用的输入/输出/耗时全记录，可回溯审计\n4. **Human-in-loop**：危险操作（重启、删除等）需要人工审批确认\n5. **RAG 辅助**：Agent 可查询知识库确认工具参数的准确性"

### Q3: "这个项目与传统的 ChatOps（如 Hubot）有什么区别？"

> "ChatOps 基于规则的匹配（关键词 → 脚本），只能处理预定义的固定场景。而 AI Agent 基于 LLM 的语义理解，可以处理模糊的自然语言请求，动态组合工具链。\n\n举例：用户说 '检查一下生产环境'——ChatOps 只能匹配固定 pattern，而 AI Agent 会分析这句话可能涉及服务器健康、Docker 状态、K8s Pod、告警等多个维度，自主决定需要调用哪些工具。此外，RAG 知识库、长期记忆、Trace 可观测性这些能力是传统 ChatOps 完全不具备的。"

### Q4: "生产环境部署需要注意什么？"

> "生产环境部署有三点关键：\n1. **JWT 密钥**：必须用 `openssl rand -hex 32` 生成强密钥，长度 ≥ 32 字节，不能包含 change-me/secret/password\n2. **数据库**：切换到 PostgreSQL，覆盖默认密码\n3. **CORS**：生产环境 CORS 不能是 `*`，需要设为具体域名\n4. **MCP**：生产环境推荐启用 MCP 以获取完整工具链\n5. **环境变量**：`ENVIRONMENT=production` 触发生产安全门禁"

### Q5: "OpenTelemetry 和 Prometheus 指标怎么用？"

> "OpenTelemetry 在启动时自动初始化，实现了 Agent Trace 的自动埋点。Prometheus 指标包括三类：\n- **HTTP 指标**：请求量、延迟、状态码分布\n- **LLM 指标**：调用次数、延迟、Token 用量\n- **Agent 指标**：执行次数、成功率、工具调用数\n- **MCP 指标**：工具调用量、错误率\n指标通过 /metrics 端点暴露，Grafana 面板开箱即用。"

---

## 7. 面试简历关键词

| 方向 | 关键词 |
|------|--------|
| **AI Agent** | LangGraph, StateGraph, Function Calling, Tool Calling, Agent Loop |
| **运维工具** | MCP Protocol, Kubernetes, Docker, SSH, Prometheus, Grafana |
| **知识管理** | RAG, pgvector, Embedding, Enterprise Knowledge Hub, 多租户 |
| **后端架构** | FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, OpenTelemetry |
| **系统设计** | 多租户隔离, RBAC, Fernet 加密, 优雅降级, 全链路跟踪 |
| **前端** | React 18, TypeScript, Vite, SSE, WebSocket, TailwindCSS |
| **部署** | Docker Compose, Dockerfile, CI/CD, Helm Chart, 生产安全门禁 |

---

## 8. 30 秒 / 1 分钟 / 3 分钟版本速查

| 时长 | 内容 |
|------|------|
| **30 秒** | 一句话介绍 + 一个 Demo 场景（502 故障诊断：自然语言 → Agent 自动调 K8s 工具 + 查知识库 → 生成报告） |
| **1 分钟** | 加技术栈（LangGraph + MCP + RAG + FastAPI）+ 项目规模（50+ 后端文件, 280+ 测试, 35+ 工具） |
| **3 分钟** | 加架构细节（StateGraph 条件边、Tool Router 合并、RAG 多租户隔离、MCP 动态发现）+ 一个技术挑战（MCP 稳定性、RAG 检索质量优化） |

---

> **文档版本**: v3.3.0 | **更新日期**: 2026-08-18 | **返回**: [README](../README.md)