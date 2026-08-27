# Changelog

All notable changes to this project are documented in this file.

## [v3.3.0] hardening

- SSH 托管凭据 Fernet 加密落库（兼容历史明文读取）
- WebSocket `/ws/chat/{id}` 要求 JWT，并校验会话归属；错误不再回传 traceback
- `GET /api/server/status` 需要登录；生产环境 `/api/chat` 与 `/api/chat/stream` 必须登录
- RAG 文档表述与实现对齐：JSON embedding + 应用层余弦相似度（未启用 pgvector 扩展）
- 修复审批令牌绑定提出者，禁止一句「确认」误批他人操作
- SSE Agent 工作线程使用独立数据库会话
- 生产环境默认关闭公开注册与 OpenAPI UI；`/metrics` 可配置 `METRICS_TOKEN`
- Redis 生产 healthcheck 带密码；Embedding / SSH 连接缓存设上限
- Redis 可用时跨进程限流，不可用回退内存限流；告警列表设上限
- 生产 Helm 关闭公开注册；健康检查如实反映 LLM / 采集线程状态
- 前端补齐 ESLint 10 flat config，CI lint 作为真实门槛（允许少量 any 警告）

## [v3.3.0] - 2026-08-18 — Enterprise Knowledge Hub

### Added

- AI SRE Agent (LangGraph planning, reasoning, tool calling)
- MCP integration (Kubernetes, Docker, SSH, system tools)
- Enterprise Knowledge Hub (Feishu connector, encrypted credentials, sync pipeline)
- RAG pipeline (chunk → embed → pgvector → `knowledge_search`)
- Kubernetes diagnosis (pods, logs, events, 502 / OOM / CrashLoop)

### Testing

- Knowledge Hub suite: **28/28 passed**

### 新功能

- **企业知识 Hub（Knowledge Hub）**：多租户知识库，支持飞书 Wiki 连接器、外部知识源管理、凭据加密存储
- **统一文档提供者**：Agent 知识搜索同时覆盖手动文档和 Hub 文档，organization_id 隔离
- **知识同步 Pipeline**：validate → list → fetch → parse → ingest_text，自动定时同步
- **Agent 知识工具增强**：`knowledge_search` / `knowledge_get_document` 支持多租户过滤
- **Demo 数据包**：`demo/` 目录包含 502 故障场景、K8s 日志、Nginx 日志、知识库文档 + 一键导入脚本
- **前端 Knowledge Hub 页面**：`/knowledge` 路由，文档管理 / 知识源管理 / 语义搜索 / 同步历史

### 🔧 优化

- **多租户隔离**：Organization 级别数据和文档隔离，RBAC 三角色（Admin / DevOps / Viewer）
- **凭据安全**：外部知识源 Token/Secret 使用 Fernet 加密存储
- **RAG 引擎增强**：支持 organization_id + user_id 双层过滤
- **前端导航升级**：新增 Knowledge Hub 入口，旧路由 `/dashboard` `/chat` 自动重定向
- **版本号升级**：`APP_VERSION = "3.3.0"`，所有文档和构建统一更新

### 📚 文档

- 新增 `docs/V3.3_FINAL_AUDIT.md` — 最终审计报告
- 新增 `docs/V3.3_RELEASE_NOTES.md` — 版本发布说明
- 新增 `docs/ARCHITECTURE.md` — 完整架构文档
- 新增 `docs/DEMO_GUIDE.md` — 5 分钟面试演示指南
- 重写 `README.md` — CNCF 风格开源项目 README + Why AI SRE 章节
- 新增 `RELEASE_CHECKLIST.md` — 9 大类 40+ 项发布检查清单
- 新增 `docs/INTERVIEW_GUIDE.md` — SRE 岗位面试指南

### 🧪 测试

- 新增 `tests/test_v33_knowledge_hub.py` — 28 项 v3.3 专项测试（全部通过 ✅）
- 覆盖：多租户隔离、凭据加密、Connector 注册、同步 Pipeline、统一提供者、API RBAC、回归测试

---

## [v1.3.0] - 2026-08-17

### 🚀 新功能

- **RAG 知识库系统**：支持文档导入 (.md/.txt)、文本切分、向量化、语义检索
- **Agent 长期记忆**：自动检索历史故障记录和解决方案，经验可复用
- **知识库管理页面**：Web 端上传/查看/删除/搜索知识文档
- **知识库 API**：`POST /api/knowledge/upload`、`GET /api/knowledge`、`DELETE /api/knowledge/{id}`、`POST /api/knowledge/search`

### 🔧 优化

- **Agent 提示词升级**：动态注入 RAG 知识库和长期记忆上下文
- **数据库模型扩展**：新增 `KnowledgeDocument` 和 `KnowledgeChunk` 模型
- **配置系统增强**：新增 `embedding_model` 和 `embedding_dimension` 配置项
- **前端导航升级**：侧边栏新增\"知识库\"入口

### 🧪 测试

- 新增 `tests/test_rag.py`：33 项 RAG 专项测试
- 后端测试总数：214 项（全部通过）
- 前端测试总数：25 项（全部通过）

### 📚 文档

- 新增 `docs/demo/rag-demo.md`：RAG 知识库详细演示文档
- 新增 `DAY17_RAG_MEMORY_REPORT.md`：Day 17 完成报告
- README 升级：新增 AI 知识库能力说明和架构图

---

## [v1.2.0] - 2026-08-10

### 🚀 新功能

- **可观测性平台**：集成 Prometheus 指标采集和 Grafana 可视化
- **智能告警系统**：基于规则的告警引擎 + AI 告警分析 + 多渠道通知（飞书/钉钉/企业微信）
- **前端监控面板**：Web 端实时监控指标展示

### 🔧 优化

- API 限流中间件
- 请求日志中间件
- 启动/关闭事件管理（采集线程 + 告警线程）

### 🧪 测试

- 新增 `test_monitoring.py`、`test_monitoring_api.py`、`test_alert.py`

---

## [v1.1.0] - 2026-08-06

### 🚀 新功能

- **企业 Web 控制台**：React + TypeScript 前端，7 个页面
- **用户认证系统**：JWT 认证 + bcrypt 密码 + RBAC 三级角色
- **WebSocket 实时轨迹**：Agent 执行过程实时推送
- **Kubernetes 运维工具**：Pod/Node 查看、故障诊断引擎
- **前端测试体系**：8 项 Vitest 测试

### 🔧 优化

- 前后端分离架构
- CORS 和安全配置
- 完整的 API 文档

### 🧪 测试

- 新增前端测试套件
- 新增 E2E 集成测试

---

## [v1.0.0] - 2026-07-30

### 🚀 新功能

- **AI Agent 引擎**：基于 LangGraph + DeepSeek API 的运维 Agent
- **运维工具集**：服务器健康检查、Docker 管理、系统日志查询
- **SSH 远程运维**：基于 paramiko 的安全远程执行
- **REST API**：FastAPI 构建的完整 API 层
- **SQLite 数据库**：用户、会话、消息持久化
- **Docker 部署**：一键 Docker Compose 启动

### 🧪 测试

- 初始测试套件：工具层、Agent 流程、数据库、认证
- CI/CD 流水线搭建（GitHub Actions）