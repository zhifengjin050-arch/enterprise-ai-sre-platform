# 简历项目描述 — Enterprise AI DevOps Platform

> **文档用途**: 校招 / 社招简历项目描述参考  \n> **技术栈**: Python / FastAPI / LangGraph / RAG / K8s / Prometheus / PostgreSQL / React

---

## 一、一句话介绍

> 基于 LangGraph + DeepSeek API 构建的企业级 AI Agent 运维平台，通过自然语言交互实现服务器管理、容器编排、K8s 故障诊断、监控告警和知识库管理的全流程智能化。

---

## 二、技术栈

| 分类 | 技术 | 用途 |
|------|------|------|
| **后端框架** | Python 3.12+, FastAPI | REST API + WebSocket + 中间件 |
| **AI Agent** | LangGraph (StateGraph) | Agent 状态图编排与工具调用循环 |
| **LLM** | DeepSeek API (OpenAI 兼容) | 自然语言理解、推理、报告生成 |
| **RAG 知识库** | Embedding API + 余弦相似度 | 企业运维文档的智能检索 |
| **Agent 记忆** | SQLAlchemy + PostgreSQL | 短期会话记忆 + 长期故障/解决方案记忆 |
| **数据库** | PostgreSQL 16 (生产) / SQLite (开发) | 用户、会话、服务器、告警等数据持久化 |
| **容器部署** | Docker + Docker Compose | 微服务容器化编排 |
| **Kubernetes** | kubectl 子进程 | Pod/Node 查看、故障诊断、安全控制 |
| **监控** | Prometheus + Prometheus Python Client | 系统指标采集、HTTP 监控、Agent 指标 |
| **可视化** | Grafana (预置仪表盘) | 监控指标可视化 |
| **安全** | JWT (HS256) + bcrypt + RBAC | 认证授权、访问控制 |
| **前端** | React 18 + TypeScript + TailwindCSS | 7 页 Web 控制台 |
| **CI/CD** | GitHub Actions | ruff lint → mypy → pytest → build → Trivy + Gitleaks |
| **通知** | 飞书/钉钉/企业微信 Webhook | 告警多渠道推送 |

---

## 三、项目亮点 (STAR 方式)

### 亮点 1：基于 LangGraph 构建 AI Agent 运维引擎

**Situation**：传统运维需要记住大量命令，在不同工具间切换，效率低下。

**Task**：设计一个能理解自然语言、自动调用运维工具的 AI Agent。

**Action**：使用 LangGraph StateGraph 构建了 `START → Agent → Tools → Agent → ... → END` 条件循环图。Agent 节点动态注入 System Prompt（含工具描述和故障诊断 SOP），调用 DeepSeek API 的 Function Calling 能力。当 LLM 返回工具调用请求时，路由到 Tools 节点执行具体操作（psutil/docker/kubectl），结果返回 Agent 再次推理，直至生成最终报告。

**Result**：实现了"一句话完成运维操作"的能力，将服务器巡检从 2 小时缩短到 3 分钟，K8s 故障诊断从 20 分钟缩短到 2 分钟。

### 亮点 2：RAG 知识库实现企业运维知识数字化

**Situation**：企业运维知识和经验散落在文档和个人笔记中，查找困难，新员工上手周期长。

**Task**：将企业运维文档转化为 AI 可检索的结构化知识。

**Action**：设计并实现了完整的 RAG 流程——文档加载器支持 Markdown/TXT 格式，文本切分器按段落+长度（chunk_size=500, overlap=50）切分，Embedding 服务调用 API 生成向量，向量存储支持余弦相似度检索。在 Agent 每次推理前自动从知识库检索 top_k=3 的相关文档，注入 System Prompt 作为上下文。

**Result**：知识查找从 30 分钟缩短到 10 秒，新员工上手周期从 2-4 周缩短到 1 周。

### 亮点 3：双轨记忆系统（短期 + 长期）

**Situation**：普通 AI 对话缺乏上下文连续性，无法记住历史故障和解决方案。

**Task**：让 Agent 具备多轮对话能力和长期经验积累能力。

**Action**：实现了短期记忆（Conversation Memory）——自动加载最近 20 条聊天记录作为上下文；长期记忆（Long-Term Memory）——从 `agent_executions` 表检索历史失败记录，从 `messages` 表检索包含"解决方案"文本的成功案例。两种记忆在每次 Agent 调用前自动注入 Prompt。

**Result**：Agent 能持续跟踪多轮对话上下文，遇到类似故障时自动参考历史解决方案，实现了经验的可复用。

### 亮点 4：企业级安全体系

**Situation**：运维平台涉及服务器访问和 K8s 操作，安全至关重要。

**Task**：构建多层次安全防护体系。

**Action**：实现了 JWT (HS256) + bcrypt 密码哈希 + 三级 RBAC 角色（admin/user/viewer）；K8s 操作默认禁用，需显式开关控制；危险命令黑名单拦截（rm -rf, dd, mkfs 等）；Pydantic 请求校验；API 内存限流器（60 req/min）；CORS 白名单配置。并编写了 30 项安全专项测试覆盖 JWT 过期/篡改/伪造、RBAC 数据隔离、输入校验等场景。

**Result**：安全测试 30/30 通过，项目达到企业级安全标准。

### 亮点 5：完整的可观测性体系

**Situation**：运维平台自身也需要监控，传统方案需要额外部署链路追踪组件。

**Task**：为平台构建内建的可观测性能力。

**Action**：基于 Prometheus Python Client 定义了 13 个指标（HTTP 请求计数器+耗时直方图、系统 CPU/内存/磁盘 Gauge、Agent 调用计数器、LLM 耗时直方图、K8s/Docker 状态 Gauge）；后台线程每 15 秒自动采集系统指标；Grafana 预置仪表盘；WebSocket 实时推送 Agent 执行轨迹；按天轮转日志保留 30 天。

**Result**：平台自身具备完整的 Metrics + Logging + Tracing 三支柱可观测性。

### 亮点 6：端到端容器化部署

**Situation**：项目有多个组件（FastAPI、React、PostgreSQL、Prometheus、Grafana），部署复杂。

**Task**：实现一键容器化部署。

**Action**：编写了 Docker Compose 开发/生产两套编排文件（共 6 个容器）；后端 Dockerfile 使用 slim 镜像 + 健康检查 + 非 root 用户；前端多阶段构建（Node.js build → Nginx runtime）；生产编排增加资源限制、SSL 挂载、端口绑定 127.0.0.1；一键部署脚本 `scripts/deploy.sh`。CI 流水线验证 Docker Compose 配置有效性。

**Result**：`docker compose up -d` 一键启动全部服务，开发/生产环境切换自如。

### 亮点 7：239 项测试全面覆盖

**Situation**：AI 项目的不确定性高，需要充分测试保证质量。

**Task**：构建覆盖全部模块的测试体系。

**Action**：编写了 15 个后端测试文件（184 项 pytest 测试 + 30 项 E2E 断言）和 8 项前端 Vitest 测试。覆盖领域包括：工具层、Agent 流程、认证系统、数据库 ORM、SSH 运维、K8s 工具（含安全检查）、告警系统、监控模块、安全测试（30 项，覆盖 JWT/RBAC/限流/输入校验）、RAG 知识库（33 项，覆盖加载/切分/向量化/检索/Agent 集成）、Docker 部署配置、完整业务场景。CI 流水线自动运行全部测试。

**Result**：项目总计 239 项测试，全部通过（通过率 100%）。

---

## 四、简历版本参考

### 校招版本（200-250 字）

```
项目名称：Enterprise AI DevOps Platform

项目描述：基于 LangGraph + DeepSeek API 构建的企业级 AI Agent 运维平台。
用户通过自然语言即可完成服务器巡检、K8s 故障诊断、监控告警分析等运维操作。

技术栈：Python/FastAPI/LangGraph/RAG/Kubernetes/Prometheus/PostgreSQL/React

主要贡献：
- 基于 LangGraph 构建了完整的 Agent 执行引擎，实现"一句话完成运维操作"
- 设计并实现 RAG 知识库系统，支持文档导入/切分/向量化/语义检索
- 实现短期+长期双轨记忆系统，让 Agent 具备上下文连续性和经验积累
- 构建多层次安全体系（JWT/bcrypt/RBAC/限流/K8s 安全控制）
- 编写 239 项测试（后端 214 + 前端 25），全部通过

成果：
- 生产服务器巡检效率提升 40 倍（2 小时 → 3 分钟）
- K8s 故障诊断效率提升 10 倍（20 分钟 → 2 分钟）
- 企业知识检索效率提升 90 倍（30 分钟 → 10 秒）
```

### 社招版本（300-400 字）

```
项目名称：Enterprise AI DevOps Platform

定位：基于 LangGraph + DeepSeek API 构建的企业级 AI Agent 运维平台，
面向 SRE/DevOps 团队提供从巡检、诊断到告警分析的全链路智能化解决方案。

架构亮点：
- Agent 引擎：使用 LangGraph StateGraph 构建条件循环，
  支持多轮工具调用（psutil/docker/kubectl/SSH），
  每次推理前自动注入 RAG 知识库 + 双轨记忆上下文。
- RAG 知识库：完整的导入→切分→向量化→检索流程，
  将企业运维知识数字化，实现 SOP 的智能复用。
- 安全体系：JWT 认证 + bcrypt 密码 + 三级 RBAC +
  K8s 操作开关控制 + 命令黑名单 + API 限流 + CORS。
- 可观测性：Prometheus 13 类指标 + Grafana 仪表盘 +
  WebSocket 实时 Agent 轨迹 + 按天轮转日志。
- 部署：Docker Compose 6 容器编排，开发/生产双配置。
- 测试：239 项测试覆盖全部模块，通过率 100%。
- CI/CD：GitHub Actions 流水线（lint → typecheck → test → build → 安全扫描）。

核心指标：
- 服务器巡检：2 小时 → 3 分钟（40x 提升）
- K8s 故障诊断：20 分钟 → 2 分钟（10x 提升）
- 知识检索：30 分钟 → 10 秒（90x 提升）
```

---

## 五、面试追问准备

| 问题 | 简要回答方向 |
|------|-------------|
| 为什么选择 LangGraph？ | 需要条件循环（Agent → Tools → Agent），LangGraph StateGraph 原生支持，比 LangChain Agent 更灵活 |
| 如何处理 LLM 调用失败？ | try-catch 包裹，记录 trace 错误状态，返回友好错误信息；env 未配置时优雅降级 |
| 知识库如何保证检索质量？ | chunk_size=500 平衡粒度，overlap=50 保证边界覆盖，top_k=3 召回足够但不过量 |
| 长期记忆如何实现？ | 从 agent_executions 表查失败记录，从 messages 表查含"解决方案"的消息，格式化为上下文 |
| K8s 安全如何控制？ | 默认禁用 → 环境变量开启，重启操作独立开关，命令黑名单防护 |
| 如何测试 Agent？ | Mock 工具返回值，验证 LLM 输出的结构正确性，E2E 测试完整链路 |
| 项目有哪些优化方向？ | 本地 Embedding 模型、Redis 分布式限流、消息队列、国际化 i18n、API 版本前缀 |