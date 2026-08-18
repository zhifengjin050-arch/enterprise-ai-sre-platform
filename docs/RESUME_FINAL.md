# 简历项目描述 — 最终版

> **项目名称**：Enterprise AI DevOps Platform
> **项目定位**：企业级 AI 智能运维平台
> **技术栈**：FastAPI · LangGraph · React · PostgreSQL · Docker · Kubernetes · Prometheus

---

## 版本 1：校招/应届生版本

### 项目概述

> **Enterprise AI DevOps Platform** 是一个基于 LLM Agent 的企业级智能运维平台。用户通过自然语言即可完成服务器巡检、K8s 故障诊断、监控告警分析等运维操作。项目完全独立开发，涵盖 AI Agent、Web 控制台、RAG 知识库、监控告警等完整功能模块，239+ 项测试全部通过。

### 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Python, FastAPI, SQLAlchemy, LangGraph |
| 前端 | React 18, TypeScript, Vite, TailwindCSS |
| AI | DeepSeek LLM, RAG, Embedding, Function Calling |
| 数据库 | PostgreSQL, SQLite, Alembic |
| 运维 | Docker, Kubernetes (kubectl), SSH (paramiko) |
| 监控 | Prometheus, Grafana |
| CI/安全 | GitHub Actions, Trivy, Gitleaks |

### 项目亮点

1. **AI Agent 智能引擎**：基于 LangGraph 状态图构建，支持多步骤工具调用、RAG 知识检索和长期记忆，可自主完成复杂的运维诊断任务
2. **RAG 知识库系统**：实现了完整的 RAG 流程（文档加载 → 文本分割 → Embedding → 向量存储 → 语义检索），让 Agent 能够引用企业运维文档回答问题
3. **全栈工程能力**：独立完成从后端 API（FastAPI, 15+ 端点）到前端 SPA（React + TypeScript, 7 个业务页面）的全栈开发
4. **企业级功能完整**：包含 JWT 认证、RBAC 权限控制、速率限制、WebSocket 实时推送、操作审计日志等企业级特性
5. **DevOps 工具链集成**：深度集成 SSH 远程管理、Docker 容器管理、Kubernetes Pod 诊断、Prometheus 监控、Grafana 可视化
6. **质量保障体系**：239+ 项测试全部通过（后端 214+、前端 25），CI/CD 流水线含 Lint/TypeCheck/Test/Build/Security Scan
7. **文档完整度高**：项目包含完整的 README、API 文档、部署指南、验收报告、面试指南、Demo 脚本

---

## 版本 2：1-3 年经验版本

### 项目概述

> **Enterprise AI DevOps Platform** 是一个企业级 AI Agent 运维系统，将 LLM（DeepSeek V4 Flash）与 DevOps 工具链（SSH/Docker/K8s/Prometheus/Grafana）深度集成。系统采用 FastAPI + LangGraph + React + PostgreSQL 架构，通过 LangGraph 状态图编排 Agent 执行流程，结合 RAG 知识库和长期记忆实现智能运维。项目从零到一独立架构设计并完成开发，后端 47 个 Python 文件、前端 7 个业务页面、239+ 测试全部通过，已通过完整运行验收。

### 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 后端框架 | FastAPI + Uvicorn | REST API + WebSocket |
| Agent 引擎 | LangGraph StateGraph | 多步骤任务编排 |
| LLM | DeepSeek API (Function Calling) | 自然语言理解与推理 |
| 数据库 | PostgreSQL + SQLAlchemy + Alembic | 8 张表，数据持久化与迁移 |
| 前端 | React 18 + TypeScript + Vite + TailwindCSS | Web 控制台 |
| 容器化 | Docker Compose (dev/prod) + 多阶段构建 | 容器部署 |
| 工具 | paramiko (SSH), docker-py, kubectl, psutil | 运维工具执行 |
| 监控 | Prometheus + Grafana | 指标采集与可视化 |
| CI/CD | GitHub Actions + Trivy + Gitleaks | 自动化与安全 |

### 项目亮点

1. **企业级系统设计**：采用分层架构（Frontend → API → Agent → Tools → Infrastructure），模块间通过清晰的接口解耦，支持水平扩展。Agent 层集成短期记忆（对话历史）、长期记忆（历史故障）和 RAG 知识库三重上下文，提升回答准确性

2. **AI Agent 工程化落地**：基于 LangGraph 状态图实现 Agent 工作流，支持条件路由（判断是否需要工具调用）和循环执行（多轮工具调用后汇总结果）。设计了动态 System Prompt 机制，根据对话上下文和知识库检索结果实时生成提示词

3. **RAG 知识库系统设计**：实现端到端 RAG 流水线，包含文档加载器（Markdown/TXT）、文本分割器（500 字符窗口 + 50 字符重叠）、Embedding 服务（API 调用 + 降级方案）、pgvector 向量存储（余弦相似度搜索）。知识库更新后实时生效，无需重新训练

4. **DevOps 工具链深度集成**：通过统一的工具注册机制将 SSH（远程服务器管理）、docker-py（容器操作）、kubectl（K8s 诊断）和 psutil（系统指标）注册到 Agent 工具集。设计了多层安全机制：K8s 双开关、SSH 命令黑名单、操作审计日志

5. **全栈工程化实践**：测试覆盖 239+ 项（后端单元/集成/场景/安全 + 前端 Vitest），CI/CD 流水线执行 Lint/TypeCheck/Test/Build 全流程，Trivy 容器扫描 + Gitleaks 密钥扫描保障安全

6. **生产就绪部署方案**：提供开发（docker-compose.yml）和生产（docker-compose.prod.yml）两套编排配置，支持 PostgreSQL + Gunicorn + Nginx 的生产部署模式，.env 环境变量管理敏感配置

7. **项目包装完整性**：包含 15+ 份专业文档（架构设计、API 文档、部署指南、验收报告、面试指南、Demo 脚本），4 个可演示的企业场景，可直接用于面试展示和 GitHub 开源

### 项目数据

| 指标 | 数值 |
|------|:----:|
| 后端代码 | 47 个 Python 文件，覆盖 Agent/API/数据库/工具/监控/告警/RAG |
| 前端页面 | 7 个业务页面（登录/Dashboard/Chat/服务器/K8s/监控/知识库） |
| 测试覆盖 | 239+ 项（后端 214+、前端 25），通过率 100% |
| API 端点 | 15+ REST 端点 + WebSocket |
| 数据库表 | 8 张（用户/会话/消息/服务器/Agent执行/告警/知识文档/知识块） |
| Prometheus 指标 | 13 类（HTTP/Agent/LLM/系统资源） |
| 容器镜像 | 5 个（前端/后端/PostgreSQL/Prometheus/Grafana） |

---

## 简历项目描述模板

### 一句话版本

> Enterprise AI DevOps Platform：基于 LLM Agent 的企业级智能运维平台，通过自然语言驱动服务器巡检、K8s 故障诊断、监控告警等运维操作。

### 100 字版本

> 基于 FastAPI + LangGraph + React + PostgreSQL 构建的 AI Agent 运维系统。用户通过自然语言即可完成服务器健康检查、Kubernetes 故障诊断、监控告警分析等复杂运维任务。底层集成 RAG 知识库（企业文档增强）和长期记忆（历史经验复用），239+ 项测试全面覆盖。已通过完整运行验收。

### 200 字版本（推荐用于简历）

> 独立开发的基于 LLM Agent 的企业级智能运维平台，后端 FastAPI + LangGraph（47 个 Python 文件），前端 React + TypeScript（7 个页面），数据库 PostgreSQL + SQLAlchemy。核心亮点：① LangGraph 状态图编排 Agent 多步骤工具调用，支持 SSH/Docker/K8s 等 11 种运维工具；② RAG 知识库实现文档上传→向量化→语义检索→Agent 引用的完整流程；③ Prometheus + Grafana 可观测性（13 类指标、预置仪表盘）；④ JWT 认证 + RBAC 三角色 + 速率限制 + 安全扫描。239+ 项测试全部通过，CI/CD 全自动化，4 个企业场景可演示。

---

*END OF DOCUMENT*