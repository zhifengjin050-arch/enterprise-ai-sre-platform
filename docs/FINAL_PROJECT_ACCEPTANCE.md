# Enterprise AI DevOps Platform v1.3.0
# 最终企业级验收报告（FINAL PROJECT ACCEPTANCE）

> **验收日期**：2026-08-17  
> **验收角色**：资深 SRE 架构师 / AI Agent 工程负责人 / 企业软件验收负责人  
> **验收原则**：不修改业务代码、不新增功能、不优化代码；结论仅基于真实代码与真实运行结果  
> **项目路径**：D:\代码项目\AI Agent项目\项目1：AI DevOps Assistant 在线版  
> **版本**：v1.3.0 Release

---

## 0. 验收结论摘要

| 项 | 结论 |
|---|---|
| 总体判定 | **有条件通过（Conditional Pass）** |
| 后端可运行性 | **通过**（本机 uvicorn 成功启动，核心 API 可用） |
| 前端测试 | **通过**（Vitest 25/25） |
| 前端生产构建 | **未通过**（TypeScript 编译错误 8 处） |
| Agent 端到端 | **未完整通过**（本轮 DEEPSEEK_API_KEY 无效，LLM 返回 401） |
| RAG 链路 | **通过**（上传→切分→向量化→检索，相关度 0.7172） |
| Memory 设计 | **代码存在且可注入**（短期+长期；本轮受 LLM Key 限制未能端到端联调） |
| 安全 | **中等偏上**（JWT/RBAC/限流存在；Compose 默认口令与端口暴露需整改） |
| 综合评分 | **78 / 100** |

**一句话结论**：这是一个结构完整、工程化程度较高的企业级 AI DevOps Agent 平台原型，核心 API / RAG / 监控告警 / 前端单测已验证；当前阻塞项是 LLM API Key 配置与前端 TypeScript 构建错误。

---

## 1. 项目介绍（第一部分：项目定位验收）

### 1.1 这个项目是什么？

**一句话介绍**：基于 LangGraph + DeepSeek 的企业智能运维平台，用自然语言驱动服务器、Docker、Kubernetes、监控告警与运维知识库。

它不是聊天机器人，而是：

用户自然语言 → FastAPI → LangGraph Agent → Tool Calling → 真实运维数据 → AI 分析报告

### 1.2 解决企业什么问题？

| 企业痛点 | 项目应对 |
|---|---|
| 故障排查依赖个人经验，新人成本高 | Agent 自动调用工具并生成结构化报告 |
| 多系统割裂（SSH/Docker/K8s/监控） | 统一自然语言入口 |
| 运维知识难沉淀 | RAG 知识库 + 长期记忆 |
| 夜间响应慢 | Prometheus/Grafana + 内置告警引擎 + AI 初诊能力 |

### 1.3 面向哪些用户？

- SRE / DevOps 工程师（日常巡检、故障定位）
- 平台/基础设施团队负责人（统一运维入口）
- 初级运维人员（降低命令行门槛）
- 面试/作品集展示场景（完整 Agent + DevOps 工程链路）

### 1.4 适合哪些岗位？

- SRE / Site Reliability Engineer
- DevOps / Platform Engineer
- AI Agent / LLM Application Engineer
- 后端工程师（FastAPI + 工程化）

### 1.5 与传统 DevOps/SRE 工具的区别

| 维度 | 传统工具（Prometheus/Grafana/kubectl/脚本） | 本项目 |
|---|---|---|
| 交互 | GUI / CLI / Dashboard | 自然语言 + 工具自动编排 |
| 决策 | 人看指标再判断 | Agent 自动选工具并解释 |
| 知识 | 分散在 Wiki/人脑 | RAG + Memory 可检索 |
| 链路 | 多系统切换 | 统一 Agent 闭环 |

### 1.6 企业应用场景与价值

**场景**：服务器巡检、Docker 异常排查、K8s Pod 重启诊断、告警初诊、运维 SOP 检索。  
**价值**：降低 MTTR、降低操作门槛、沉淀企业运维知识、形成可演示的 AI+SRE 工程能力。

---

## 2. 技术架构（第二部分：代码架构审计）

### 2.1 完整架构图（基于真实目录与代码）

`
┌──────────────────────────────┐
│  React SPA (Vite + TS)       │
│  Login / Dashboard / Chat /  │
│  Servers / K8s / Monitoring /│
│  Knowledge + WebSocket Trace │
└──────────────┬───────────────┘
               │ HTTP / WS
               ▼
┌──────────────────────────────┐
│ FastAPI Backend              │
│ Auth(JWT/RBAC) + RateLimit   │
│ REST APIs + /health /metrics │
│ LangGraph Agent Engine       │
│  ├─ Prompt                   │
│  ├─ RAG Retriever            │
│  ├─ Short/Long Memory        │
│  └─ Tool Executor            │
└───────┬───────────┬──────────┘
        │           │
        ▼           ▼
   DeepSeek API   Tools(18)
   (LLM)          ├ server_health / logs
                  ├ docker_status / docker_logs
                  ├ k8s_* / kubectl_*
                  └ ssh_*
        │
        ▼
   PostgreSQL/SQLite
   (8 tables)
        │
        ▼
   Prometheus ← /metrics
   Grafana Dashboard
`

### 2.2 前端审计

| 项 | 真实结果 |
|---|---|
| 技术栈 | React 18 + TypeScript + Vite + TailwindCSS + React Router v6 + Axios + Vitest |
| 页面数量 | 7 个业务页：Login、Dashboard、Chat、Servers、Kubernetes、Monitoring、Knowledge |
| 路由设计 | 公开 /login + 受保护业务路由（AuthContext + Token） |
| 组件 | Layout / Sidebar / Header / StatusBadge / ServerCard / AgentTrace |
| 前端测试 | 5 个测试文件，**25 passed** |
| 构建状态 | 
pm run build **失败**（Knowledge.tsx / Monitoring.tsx TS 类型错误） |

### 2.3 后端审计

| 项 | 真实结果 |
|---|---|
| 框架 | FastAPI + Uvicorn |
| 模块划分 | agent / alert / auth / database / llm / memory / monitoring / rag / tools |
| 数据模型（8 表） | users, conversations, messages, managed_servers, agent_executions, alerts, knowledge_documents, knowledge_chunks |
| API 范围 | Auth、Chat、Conversations、Servers、Knowledge、Monitoring、Alerts、K8s、Agent Stats、WebSocket、health、metrics |

### 2.4 AI Agent 审计

| 项 | 真实结果 |
|---|---|
| 流程 | LangGraph：agent_node ↔ tools_node → final_report |
| Prompt | pp/agent/prompts.py 含运维角色、诊断流程、报告格式、RAG/Memory 使用规范 |
| Tool 调用 | Function Calling；注册工具 **18** 个（实测 get_all_tools()） |
| LLM 接入 | pp/llm/client.py OpenAI 兼容接口（DeepSeek/SiliconFlow） |
| 状态管理 | TypedDict AgentState（messages/tool_calls/trace/final_report） |
| Trace | 分析用户需求 → 调用工具 → AI 生成报告（可 WebSocket 推送） |

**已注册工具（真实输出）**：
server_health, docker_logs, docker_status, system_logs, k8s_deployments, k8s_pod_logs, k8s_pods, k8s_services, ssh_docker_logs, ssh_docker_status, ssh_exec, ssh_server_health, ssh_system_logs, kubectl_describe_pod, kubectl_get_nodes, kubectl_get_pods, kubectl_logs, kubectl_restart_deployment

### 2.5 RAG 链路审计（代码完整）

`
文档上传(/api/knowledge/upload)
  → loader(load_text/load_file: md/txt)
  → splitter(chunk_size=500, overlap=50)
  → embeddings(OpenAI兼容 + 降级哈希向量)
  → knowledge_chunks.embedding 存储
  → similarity_search(余弦相似度)
  → format_knowledge_context
  → Agent Prompt 注入
  → LLM 回答
`

### 2.6 Memory 审计

| 类型 | 实现 | 存储方式 |
|---|---|---|
| 短期记忆 | conversation_memory.load_conversation_history | DB messages（最多 20 条） |
| 长期记忆 | long_term_memory（失败执行 + 含“解决方案”的回复） | DB gent_executions / messages |
| Agent 注入 | agent_node 动态拼入 system prompt | 运行时检索 |

### 2.7 DevOps 能力审计

| 能力 | 代码/配置证据 |
|---|---|
| SSH | paramiko + managed_servers + ssh_* tools |
| Docker | docker-py + docker_status/logs |
| Kubernetes | k8s_ops + kubectl_* tools + 前端 K8s 页 |
| Monitoring | prometheus-client + collector 线程 + Grafana |
| Alert | 内置规则（CPU/内存/磁盘/Docker）+ 渠道记录 |

### 2.8 工程化审计

| 项 | 证据 |
|---|---|
| Docker Compose | postgres/backend/frontend/prometheus/grafana（5~6 服务） |
| CI/CD | .github/workflows/ci.yml（backend/frontend/docker check） |
| 测试体系 | tests/ 15 个后端测试文件 + frontend 5 个测试文件 |
| 安全机制 | JWT、RBAC、bcrypt、rate limit、security 测试文件 |

---

## 3. 功能清单

| 模块 | 功能 | 验收状态 |
|---|---|---|
| 认证 | 注册/登录/me/JWT | **通过（实测）** |
| 服务器状态 | /api/server/status | **通过（实测）** |
| 健康检查 | /health | **通过（实测）** |
| 监控指标 | /metrics | **通过（实测）** |
| 知识库 | upload/list/search/delete | **通过（实测 upload/list/search）** |
| Agent Chat | /api/chat | **接口可达；LLM 401（本轮 Key 无效）** |
| 前端单测 | Vitest | **25/25 通过** |
| 前端构建 | tsc + vite build | **失败（TS 错误）** |
| 告警引擎 | 启动后自动触发 | **通过（日志出现真实告警）** |

---

## 4. 真实运行验证（第三部分）

### 4.1 Backend 启动

- 启动方式：uvicorn，http://127.0.0.1:8000
- 日志确认：Application startup complete
- 数据库初始化成功（本轮 SQLite 	est.db）
- 指标采集线程启动（15s）
- 告警管理线程启动（30s）

### 4.2 接口实测记录

#### 接口：GET /health
- 结果：**200 OK**
- 响应：status=healthy, version=1.3.0, services.api/llm/database/monitoring=ok, agent=ready
- 耗时：**约 16ms（服务端记录） / 客户端约 3s（含网络与 PowerShell 开销）**

#### 接口：POST /api/auth/register
- 结果：**201 Created**
- 响应：{id:1,username:testuser,email:test@test.com,role:user}
- 耗时：**约 469ms（服务端 histogram）**

#### 接口：POST /api/auth/login
- 结果：**200 OK**
- 响应：返回 JWT access_token + user
- 耗时：**约 516ms（服务端 histogram）**

#### 接口：GET /api/auth/me（Bearer Token）
- 结果：**200 OK**
- 响应：当前用户信息
- 耗时：**约 2.5s（客户端往返，含再次登录拿 token）**

#### 接口：GET /api/server/status
- 结果：**200 OK**
- 响应：真实本机资源（CPU/内存/磁盘）
- 示例：CPU 98.1%、内存 79.9%、C: 89.8%、D: 16.2%
- 耗时：**约 1~2.9s（含 psutil 采集）**

#### 接口：GET /metrics
- 结果：**200 OK**
- 响应：Prometheus 指标（HTTP、CPU、内存、磁盘、Docker、Agent、LLM）
- 耗时：**约 4s（客户端）**

#### 接口：GET /api/knowledge（空库）
- 结果：**200 OK，[]**
- 耗时：**约 2.7s（客户端）**

#### 接口：POST /api/knowledge/upload
- 结果：**成功，文档 id=1**
- 耗时：**约 9.2s（含 embedding）**

#### 接口：GET /api/knowledge（上传后）
- 结果：**1 条文档**
- 耗时：**约 7.5s（客户端）**

#### 接口：POST /api/knowledge/search
- 结果：**命中 1 条，score=0.7172**
- 耗时：**约 10.5s（客户端）**

#### 接口：POST /api/chat
- 结果：**接口可达，返回 Agent Error**
- 原因：openai.AuthenticationError: Error code: 401 - Invalid token
- 说明：本轮启动使用无效 DEEPSEEK_API_KEY=test，**不能伪造 Agent 成功结果**

### 4.3 Frontend

| 项 | 结果 |
|---|---|
| 依赖 | 已存在 node_modules，可执行 npm test/build |
| test | **25 passed / 5 files** |
| build | **失败**：Knowledge.tsx、Monitoring.tsx 共 8 个 TypeScript 错误 |

---

## 5. Agent 能力验收（第四部分）

> 说明：本轮因 LLM API Key 无效，**场景 1~4、6~7 的端到端 LLM 推理未能真实完成**。以下区分「代码能力已具备」与「本轮运行已验证」。

### 5.1 场景1：服务器巡检

- 输入：帮我检查服务器状态
- 实测：/api/chat 进入 Agent Graph，在 gent_node 调用 LLM 时 401
- 代码预期链路：
  用户输入 → 分析用户需求 → LLM 选择 server_health → tools_node 执行 → 生成报告
- 旁证：/api/server/status 可直接获取真实服务器数据（工具层能力存在）

### 5.2 场景2：Kubernetes 故障诊断

- 输入：pod不断重启，请分析原因
- 本轮：未完成端到端（LLM Key）
- 代码证据：存在 k8s_pods / k8s_pod_logs / kubectl_describe_pod / kubectl_logs 等工具与 Prompt 中的 K8s 诊断流程

### 5.3 场景3：Docker 异常分析

- 输入：docker服务异常怎么办
- 本轮：未完成端到端（LLM Key）
- 旁证：服务启动后告警引擎真实检测到异常容器：dujiao-redis, dujiao-postgres, dujiao-mysql
- 代码证据：docker_status / docker_logs 工具已注册

### 5.4 场景4：告警分析

- 输入：数据库连接异常
- 本轮：未完成端到端（LLM Key）
- 旁证：真实告警已触发：
  - cpu_high（CPU > 80%）
  - disk_high（C: > 85%）
  - docker_unhealthy（3 个异常容器）

### 5.5 场景5：RAG 知识库（完整实测通过）

真实流程：

1. 上传文档「运维SOP-服务器重启」→ 成功，id=1  
2. 列表查询 → 1 篇文档  
3. 搜索「服务器重启步骤」→ 命中，score=**0.7172**  
4. chunk：本次文档切分为 **1 chunk**（内容较短）  
5. Agent 引用：代码层 gent_node 会在有 db 时注入 RAG 上下文；本轮因 LLM 401 未验证最终回答引用文本

记录：

| 项 | 值 |
|---|---|
| 文档数量 | 1（本轮测试库） |
| chunk 数量 | 1 |
| 检索结果 | 1 条，相关度 0.7172 |

### 5.6 场景6：Memory

| 类型 | 验证方式 | 结果 |
|---|---|---|
| 短期记忆 | 代码：conversation_memory + chat 保存 messages | 代码具备；本轮 chat 已创建 conversation_id=1，但 LLM 失败未形成有效多轮问答 |
| 长期记忆 | 代码：失败执行/解决方案摘要注入 | 代码具备；本轮无成功 Agent 执行沉淀 |
| 存储方式 | PostgreSQL/SQLite ORM 表 | **已确认** |

### 5.7 场景7：综合企业故障

- 输入：生产接口响应慢，请排查原因
- 本轮：未完成端到端（LLM Key）
- 设计能力：Agent Prompt + 多工具（server/docker/k8s/logs）支持组合排查，但需有效 LLM Key 才可验收完整闭环

### 5.8 Agent 链路模板（设计已实现）

`
用户输入
  ↓
Agent 分析（agent_node）
  ↓
RAG/Memory 注入
  ↓
LLM Function Calling
  ↓
tools_node 执行真实工具
  ↓
结果回填 messages
  ↓
再次推理 / 生成报告
  ↓
返回 report + trace
`

---

## 6. RAG 验证（汇总）

| 步骤 | 状态 | 证据 |
|---|---|---|
| 上传 | 通过 | /api/knowledge/upload 返回 id=1 |
| 解析 | 通过 | loader 支持 text/md/txt |
| 切分 | 通过 | TextSplitter chunk_size=500 |
| Embedding | 通过（可降级） | 上传耗时升高；检索可用 |
| 向量存储 | 通过 | knowledge_chunks.embedding |
| 检索 | 通过 | score=0.7172 |
| 上下文注入 | 代码通过 | agent.py 54-64 行 |
| LLM 回答引用 | 本轮未验证 | LLM 401 |

---

## 7. Memory 验证（汇总）

| 项 | 状态 |
|---|---|
| 短期记忆代码 | 存在 |
| 长期记忆代码 | 存在 |
| DB 持久化 | 存在（messages / agent_executions） |
| Agent 注入 | 存在 |
| 端到端问答验证 | 本轮受 LLM Key 限制未完成 |

---

## 8. 测试结果（第五部分）

### 8.1 Frontend（真实执行）

`
Test Files  5 passed (5)
Tests       25 passed (25)
`

- 通过数量：**25**
- 失败数量：**0**

### 8.2 Backend pytest（本轮执行受阻说明）

本轮曾尝试 python -m pytest tests/：

1. 初始环境缺少 sqlalchemy/pytest 等依赖（已补装）
2. 后续在本环境执行 pytest 时出现 capture I/O 异常（ValueError: I/O operation on closed file），未能产出稳定的通过/失败计数

因此**本报告不虚构 pytest 通过数**。  
代码侧存在完整测试资产：	ests/ 下 15 个文件（含 test_rag/test_auth/test_agent/test_security/test_k8s_tools 等）。README 标注历史“239 passed”，但以本轮真实执行为准：**后端 pytest 本轮未拿到可靠汇总结果**。

### 8.3 Total（本轮可确认）

| 套件 | 通过 | 失败 | 备注 |
|---|---|---|---|
| Frontend Vitest | 25 | 0 | 真实执行 |
| Backend pytest | N/A | N/A | 本轮未可靠汇总 |
| Frontend build | 0 | 1 | tsc 失败 |
| API smoke | 10+ | 1（chat LLM） | 真实执行 |

---

## 9. 安全报告（第六部分）

### 9.1 认证

| 检查项 | 结果 |
|---|---|
| JWT | 有（HS256），login 返回 Bearer Token，/me 校验通过 |
| 密码 | bcrypt 哈希 |
| RBAC | UserRole: admin/user/viewer |
| 限流 | 配置与代码存在 rate limit |
| 安全测试文件 | 	ests/test_security.py 存在 |

### 9.2 密钥

| 检查项 | 结果 |
|---|---|
| .env 管理 | 使用 pydantic-settings / dotenv |
| 本轮运行 | 为验收临时设置 DEEPSEEK_API_KEY=test（无效） |
| Compose 默认口令 | postgres=devops_secret，Grafana admin/admin（**风险**） |
| 端口暴露 | 5432/8000/80/9090/3000 均映射宿主机（**风险**） |

### 9.3 Docker / 容器

| 检查项 | 结果 |
|---|---|
| healthcheck | postgres/backend 有 |
| 网络 | bridge devops-net |
| 非 root | backend Dockerfile 设计为非 root（需生产复核） |
| 明文密钥进环境 | Compose 中数据库密码明文（需改为 secret） |

### 9.4 安全评分

| 维度 | 分数 | 说明 |
|---|---|---|
| 认证 | 8/10 | JWT+RBAC+bcrypt 完整 |
| 密钥 | 5/10 | 有 env 机制，但默认口令/本轮无效 Key/明文风险 |
| 容器 | 6/10 | 有 healthcheck，但端口与口令暴露 |
| **综合** | **6.5/10** | 中等偏上，可演示，生产需加固 |

---

## 10. 性能报告（第七部分）

> 以下优先采用服务端 Prometheus histogram（更接近真实处理耗时）；客户端耗时含 PowerShell/网络开销，仅作参考。

| 接口 | 平均耗时（服务端） | 备注 |
|---|---|---|
| GET /health | ~16ms | 快 |
| POST /api/auth/register | ~469ms | bcrypt 成本正常 |
| POST /api/auth/login | ~516ms | bcrypt 成本正常 |
| GET /api/server/status | ~1.0~2.9s | 含实时采集 |
| POST /api/knowledge/upload | ~9s（客户端） | 含 embedding |
| POST /api/knowledge/search | ~10s（客户端） | 含 embedding + 相似度计算 |
| POST /api/chat | 失败（401） | 未计入成功时延 |

**性能结论**：基础 API 可接受；RAG 路径受 embedding 影响明显；全量向量扫描（非 pgvector ANN）在数据量上升后会成为瓶颈。

---

## 11. 项目评分（第八部分）

| 维度 | 分数 | 依据 |
|---|---|---|
| AI Agent | 8/10 | LangGraph + Tool Calling + Trace 完整；本轮 E2E 受 Key 限制 |
| RAG | 8/10 | 上传到检索闭环实测通过；缺 PDF/ANN 优化 |
| DevOps | 8/10 | SSH/Docker/K8s/监控/告警齐全 |
| Docker | 7/10 | Compose 完整；安全加固不足 |
| Kubernetes | 7/10 | 工具与页面具备；生产能力与 RBAC 深度一般 |
| 工程化 | 8/10 | CI/CD、模块化、监控齐全 |
| 安全 | 6.5/10 | 认证较好，部署密钥/暴露面需改 |
| 测试 | 7/10 | 前端 25/25；后端测试资产丰富但本轮未可靠跑通汇总 |
| 文档 | 9/10 | docs 文档体系非常完整 |
| 企业价值 | 8/10 | 场景清晰，可演示企业痛点解决路径 |
| **总分** | **78/100** | 有条件通过 |

---

## 12. 岗位匹配分析（第九部分）

### 推荐岗位

**岗位1：SRE / Site Reliability Engineer**  
匹配点：监控告警、故障诊断、服务器/容器/K8s 巡检、SLO 思维（可扩展）

**岗位2：DevOps / Platform Engineer**  
匹配点：Docker Compose、CI/CD、Nginx、部署脚本、平台化运维入口

**岗位3：AI Agent / LLM Application Engineer**  
匹配点：LangGraph、Tool Calling、RAG、Memory、Prompt、Trace 可观测

### 竞争力分析

- **优势**：AI Agent + 真实 DevOps 工具链 + RAG/Memory + 可观测性，比“纯聊天项目”更有说服力
- **差距**：生产级安全、高并发、自动修复、MCP 标准化、完整 Agent E2E 证据链仍需补强
- **面试建议**：重点讲 Agent 决策链路、工具安全边界、RAG 降级策略、告警到诊断闭环

---

## 13. 不足分析与后续路线（第十部分）

### 13.1 当前不足（不包装）

1. **本轮 Agent E2E 未通过**：LLM API Key 无效导致 chat 401  
2. **前端生产构建失败**：Knowledge/Monitoring 存在 TypeScript 类型错误  
3. **MCP 协议未真正接入业务主链路**（设计提及，主 Agent 仍是内置 Tool Registry）  
4. **向量检索非生产级 ANN**：JSON embedding + 全量余弦扫描，数据量大后性能不足  
5. **PDF 支持不足**：loader 实际支持 md/txt（设计曾提 PDF，代码未完整落地）  
6. **自动修复能力有限**：以诊断/建议为主，执行类操作受权限与安全开关约束  
7. **K8s 生产能力不足**：偏查询与诊断，缺少完整变更审批/GitOps/多集群治理  
8. **高并发与多租户隔离不足**：适合中小规模演示，非大规模 SaaS  
9. **Compose 默认口令与端口暴露**：不适合直接上生产  
10. **后端 pytest 本轮未产出可靠汇总**：测试资产在，执行环境稳定性需再验证

### 13.2 未来路线

#### P0（必须先做）
- 配置有效 LLM API Key，补齐 Agent 7 场景端到端录像/日志证据
- 修复前端 TypeScript 构建错误，恢复 
pm run build
- 替换 Compose 默认口令，收敛端口暴露，引入 secrets

#### P1（增强企业可用性）
- pgvector / 向量索引，优化 RAG 性能
- 补齐 PDF 解析与文档权限隔离
- 打通 MCP Server 作为标准工具层
- 补齐后端 pytest CI 稳定绿

#### P2（进阶）
- 自动修复 Playbook + Human-in-the-loop 审批
- 多集群 K8s / 云资源管理
- 高并发会话与租户级配额
- 更完整的审计与合规（操作留痕、敏感命令策略）

---

## 14. 最终交付判定

| 判定项 | 结果 |
|---|---|
| 是否可作为企业 Demo / 面试项目交付 | **是** |
| 是否可直接作为生产系统上线 | **否**（需完成 P0） |
| 最终验收结论 | **有条件通过（Conditional Pass）** |
| 综合评分 | **78 / 100** |

### 放行条件（建议）

1. 有效 LLM Key 下完成至少 3 个 Agent 场景（巡检 / Docker / K8s）完整链路  
2. 前端 build 通过  
3. 生产部署密钥与端口安全整改完成  

---

## 15. 本轮验收证据清单（真实）

1. 后端启动日志：Uvicorn running on http://127.0.0.1:8000  
2. /health 返回 version=1.3.0  
3. register/login/me 成功，JWT 可用  
4. /api/server/status 返回本机真实 CPU/内存/磁盘  
5. /metrics 返回 Prometheus 指标  
6. 告警线程真实触发 cpu_high / disk_high / docker_unhealthy  
7. 知识库 upload/list/search 成功，检索 score=0.7172  
8. /api/chat 真实报错：AuthenticationError 401 Invalid token  
9. 前端 Vitest：25 passed  
10. 前端 build：8 个 TS 错误失败  
11. 工具注册数：18  
12. 数据表：8 张  

---

**报告生成时间**：2026-08-17  
**报告文件**：docs/FINAL_PROJECT_ACCEPTANCE.md  
**验收态度**：只基于真实代码与真实运行，不做虚构成功。
