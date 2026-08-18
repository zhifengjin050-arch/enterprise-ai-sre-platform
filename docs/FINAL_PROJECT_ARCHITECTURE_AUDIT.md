# Enterprise AI DevOps Platform v2.0.0 — 项目整体架构审计

> 审计日期：2026-08-17  
> 版本：v2.0.0 (MCP 集成版)

---

## 1. 项目一句话介绍

**Enterprise AI DevOps Platform** 是一个基于 **LLM Agent + MCP Protocol + RAG 知识库 + 长期记忆** 的企业级智能运维平台，通过自然语言交互实现服务器、Docker、Kubernetes、监控告警和知识库的一体化智能运维。

---

## 2. 企业痛点

| 痛点 | 传统方案 | 本项目方案 |
|------|---------|-----------|
| 故障排查依赖人工经验 | 工程师登录多台服务器逐一排查 | AI Agent 自动调用工具链诊断 |
| 多系统工具割裂 | 需要掌握 kubectl / docker / SSH / PromQL 等 | 统一自然语言入口 |
| 运维知识无法沉淀 | 经验在少数工程师脑中 | RAG 知识库持久化沉淀 |
| 夜间/节假日响应慢 | 值班工程师人工介入 | 7x24 自动故障发现+分析 |
| 历史故障无参考 | 查聊天记录/邮件 | 长期记忆自动关联历史方案 |

---

## 3. 目标用户

| 角色 | 使用场景 |
|------|---------|
| **SRE/DevOps 工程师** | 日常巡检、故障诊断、性能分析 |
| **运维团队负责人** | 查看团队运维统计、知识库管理 |
| **技术管理者/架构师** | 评估基础设施健康度、审计运维记录 |
| **面试展示/简历项目** | 展示 AI Agent + MCP + DevOps 全栈能力 |

---

## 4. 与普通 ChatGPT 运维助手的区别

| 维度 | ChatGPT | Enterprise AI DevOps Platform |
|------|---------|------------------------------|
| **工具调用** | 无，只能提供建议 | 真实执行 SSH/Docker/kubectl 等 18+ 工具 |
| **企业认证** | 无 | JWT + RBAC 三级权限 (admin/ops/viewer) |
| **知识库** | 通用知识，无法引用企业文档 | RAG 向量检索，引用企业 SOP |
| **长期记忆** | 单轮对话，无上下文持久化 | 存储历史故障和解决方案，跨会话关联 |
| **MCP 工具生态** | 无 | MCP Protocol 标准接入，可扩展第三方工具 |
| **数据安全** | 数据归 OpenAI | 本地/私有化部署，API Key 自管 |
| **监控集成** | 无 | Prometheus + Grafana 原生集成 |

---

## 5. 核心技术能力

### 5.1 AI Agent（LangGraph 工作流）

```
用户输入 → Agent 节点(LLM推理) → 需要工具? → Tools 节点 → Agent 继续分析 → 输出报告
```

- **节点**：`agent_node`（LLM 推理）+ `tools_node`（工具执行）
- **条件边**：根据是否有待执行的 tool_calls 决定继续工具调用或结束
- **动态 Schema**：每次调用刷新工具列表，支持 MCP 工具运行时发现

### 5.2 Tool Router（工具路由）

```
Agent → get_tool_schemas()
       ├── 内置工具 (18个): server_health, docker_*, k8s_*, ssh_*, kubectl_*
       └── MCP 工具 (17个): 项目2 Enterprise DevOps MCP Server 暴露
           （ENABLE_MCP=true 时同名 MCP 优先）
```

### 5.3 RAG 知识库

```
上传文档 → 文本解析 → Chunk 切分 → Embedding(128维) → 向量存储 → 语义检索 → Agent 引用
```

### 5.4 长期记忆

```
历史故障记录 + 历史解决方案 → SQLAlchemy 持久化 → Agent 自动检索 → 上下文注入
```

### 5.5 MCP Client (stdio)

```
项目1 Agent → MCPManager → MCPClient → stdio 子进程 → 项目2 MCP Server → DevOps 工具
```

---

## 6. 当前版本能力清单

### 已实现能力 (v2.0.0)

| 模块 | 状态 | 说明 |
|------|------|------|
| ✅ FastAPI 后端 | 完整 | REST+WebSocket, 1148 行 |
| ✅ React 前端 | 完整 | 7 个主要页面, 23 个 TSX/TS 文件 |
| ✅ PostgreSQL 数据库 | 完整 | 8 个核心数据表 |
| ✅ JWT 认证 | 完整 | 注册/登录/Token 验证 |
| ✅ RBAC 权限 | 完整 | admin/ops/viewer |
| ✅ LangGraph Agent | 完整 | agent_node + tools_node + 条件边 |
| ✅ Tool Calling | 完整 | 18 个内置工具 + 动态 schema |
| ✅ SSH 远程管理 | 完整 | 5 个 SSH 工具 |
| ✅ Docker 管理 | 完整 | 2 个 Docker 工具 |
| ✅ Kubernetes 管理 | 完整 | 5 个 kubectl 工具 |
| ✅ Prometheus 监控 | 完整 | /metrics + 指标采集 |
| ✅ Grafana 可视化 | 完整 | docker-compose 集成 |
| ✅ 智能告警 | 完整 | 阈值评估 + 记录持久化 |
| ✅ RAG 知识库 | 完整 | 上传/Chunk/Embedding/检索 |
| ✅ 长期记忆 | 完整 | 故障记录 + 历史方案 |
| ✅ MCP Client (stdio) | 完整 | 子进程管理 + 工具包装 |
| ✅ CI/CD | 完整 | GitHub Actions |
| ✅ Docker 部署 | 完整 | docker-compose 6 服务 |
| ✅ 企业 Demo 场景 | 完整 | 4 个场景文档 |
| ❌ LLM API Key | 过期 | SiliconFlow 返回 401 |

### 代码规模

- 后端 Python 文件: **51**
- 前端 TSX/TS 文件: **23**
- 测试文件: **17**
- MCP 模块文件: **5**
- 文档文件: **28**
- 内置工具: **18**
- MCP 工具(项目2): **17**

---

## 7. 架构评估结论

```
评估维度         评分    说明
──────────────────────────────────────────
架构完整性       9/10   Agent + Tool Router + MCP + RAG + Memory 闭环
模块化程度       9/10   app/mcp/ 独立模块，registry.py 解耦
可扩展性         8/10   MCP Protocol 支持第三方工具注册
工程化水平       9/10   FastAPI + LangGraph + Pydantic SQLAlchemy
安全设计         8/10   JWT+RBAC+gitignore，但 API Key 管理待优化
测试覆盖         8/10   239+ 测试，MCP 测试 10/10
文档完整性       9/10   28 份文档
```

**结论**: 架构设计完整，模块化程度高，具备企业级扩展能力。主要瓶颈在 LLM API Key 时效管理和 MCP 生产化配置。

---

*审计完成时间: 2026-08-17 12:55 UTC+8*