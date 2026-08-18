# Day 19 环境审计报告

> **审计日期**: 2026-08-17
> **项目版本**: v1.3.0
> **运行环境**: Windows 10.0.26200

---

## 一、环境信息

| 项目 | 版本 | 状态 |
|------|:----:|:----:|
| 操作系统 | Windows 10.0.26200 | ✅ |
| Python | 3.12.10 | ✅ |
| Node.js | 24.15.0 | ✅ |
| Docker | 29.3.1 | ✅ |
| Docker Compose | v5.1.1 | ✅ |
| npm | 随 Node.js | ✅ |

---

## 二、项目结构

```
d:\代码项目\AI Agent项目\项目1：AI DevOps Assistant 在线版\
├── app/                          # Python 后端
│   ├── agent/                    # LangGraph Agent (6 文件)
│   ├── alert/                    # 告警系统 (4 文件)
│   ├── auth/                     # JWT 认证 (5 文件)
│   ├── database/                 # SQLAlchemy ORM (4 文件)
│   ├── llm/                      # DeepSeek API 客户端 (1 文件)
│   ├── memory/                   # Agent 记忆模块 (3 文件)
│   ├── monitoring/               # Prometheus 监控 (3 文件)
│   ├── rag/                      # RAG 知识库 (7 文件)
│   ├── tools/                    # 运维工具注册中心 (7 文件)
│   ├── static/                   # 前端构建产物
│   ├── main.py                   # FastAPI 入口 (1129 行)
│   ├── config.py                 # Pydantic 配置 (61 行)
│   └── logging_config.py         # 日志配置 (69 行)
├── frontend/                     # React + TypeScript 前端
│   ├── src/                      # 源码
│   │   ├── pages/                # 7 个业务页面
│   │   ├── components/           # 6 个通用组件
│   │   ├── api/                  # Axios 封装
│   │   ├── store/                # Auth Context
│   │   └── router/               # 路由配置
│   ├── Dockerfile                # 多阶段构建
│   ├── nginx.conf                # Nginx 反向代理
│   └── package.json              # 依赖配置
├── tests/                        # 15+ 测试文件 (239 项)
├── docs/                         # 10+ 份文档
├── scripts/                      # 部署脚本 + Demo 数据
├── prometheus/                   # Prometheus 配置
├── grafana/                      # Grafana 仪表盘
├── alembic/                      # 数据库迁移 (3 版本)
├── .env.example                  # 环境变量模板
├── .env                          # 运行时环境变量
├── docker-compose.yml            # 开发环境编排
├── docker-compose.prod.yml       # 生产环境编排
├── requirements.txt              # Python 依赖
├── LICENSE                       # MIT 开源协议
├── CONTRIBUTING.md               # 贡献指南
├── CHANGELOG.md                  # 变更日志
└── README.md                     # 项目主文档
```

---

## 三、技术栈

| 层次 | 技术 | 版本 | 用途 |
|------|------|:----:|------|
| 后端框架 | FastAPI | 0.115+ | REST API + WebSocket |
| Agent 框架 | LangGraph | 1.2+ | 状态图编排 |
| LLM | DeepSeek API | — | 自然语言推理 |
| ORM | SQLAlchemy | 2.0+ | 数据库模型 |
| 数据库 | SQLite (开发) / PostgreSQL 16 (生产) | — | 数据持久化 |
| 迁移工具 | Alembic | — | 数据库版本管理 |
| 前端 | React 18 + TypeScript | 18.3 / 5.5 | Web 控制台 |
| 构建工具 | Vite | 5.4 | 前端构建 |
| 样式 | TailwindCSS | 3.4 | UI 样式 |
| 容器编排 | Docker Compose | v5.1.1 | 服务编排 |
| 监控 | Prometheus | 2.53 | 指标采集 |
| 可视化 | Grafana | 11.1 | 指标面板 |
| CI/CD | GitHub Actions | — | 自动化流水线 |
| 安全扫描 | Trivy + Gitleaks | — | 依赖/密钥扫描 |

---

## 四、服务依赖

| 服务 | 依赖 | 端口 | 启动方式 |
|------|------|:----:|---------|
| Backend (FastAPI) | PostgreSQL / SQLite, DeepSeek API | 8000 | 直接启动 / Docker |
| Frontend (Nginx) | Backend API | 80 | Docker / npm run dev |
| PostgreSQL | — | 5432 | Docker |
| Prometheus | Backend /metrics | 9090 | Docker |
| Grafana | Prometheus | 3000 | Docker |

### 外部依赖

| 依赖 | 用途 | 必需？ | 替代方案 |
|------|------|:------:|---------|
| DeepSeek API Key | LLM 推理 | 是 | 可配置其他 OpenAI 兼容 API |
| Embedding API | 向量生成 | 否 | 内置降级方案 |
| Docker | 容器部署 | 否 | 可本地直接运行 |

---

## 五、启动方式

### 方式 1：本地直接启动

```bash
# 后端
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 前端（开发模式）
cd frontend
npm install
npm run dev
```

### 方式 2：Docker Compose 启动

```bash
docker compose up -d
```

### 方式 3：生产环境部署

```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 六、环境要求

| 条件 | 最低要求 | 推荐 |
|------|---------|------|
| Python | 3.12 | 3.12+ |
| Node.js | 18 | 20+ |
| Docker | 24+ | 最新稳定版 |
| 内存 | 2GB | 4GB+ |
| 磁盘 | 1GB | 5GB+ |
| DeepSeek API Key | 必需 | 硅基流动 / DeepSeek 官方 |
| 网络 | 可访问 api.deepseek.com | — |

---

## 七、已知风险

| 风险 | 级别 | 说明 | 缓解措施 |
|------|:----:|------|---------|
| DeepSeek API 不可用 | 🟡 中 | 所有 Agent 功能依赖 LLM API | 可切换到其他 OpenAI 兼容 API |
| Embedding API 不可用 | 🟢 低 | RAG 知识库向量检索降级 | 内置固定向量降级方案 |
| SQLite 并发限制 | 🟡 中 | 开发环境使用 SQLite，不支持高并发 | 生产环境使用 PostgreSQL |
| 前端依赖版本兼容 | 🟢 低 | npm install 可能因 Node 版本失败 | 使用 Node 20+ 推荐版本 |
| Windows 路径编码 | 🟢 低 | 中文路径可能导致 PowerShell 编码问题 | 建议使用纯英文路径部署 |
| Docker 镜像拉取 | 🟡 中 | 首次启动需拉取 5 个镜像 | 网络稳定的情况下约 5-10 分钟 |