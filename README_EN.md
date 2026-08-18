# Enterprise AI SRE Autonomous Operations Platform

<p align="center">
  <img src="https://img.shields.io/badge/AI-SRE-0ea5e9?style=for-the-badge" alt="AI SRE">
</p>

<p align="center">
  <b>Enterprise AI SRE Autonomous Operations Platform</b><br>
  An AI-powered SRE Agent platform built with LangGraph, MCP and RAG for autonomous infrastructure diagnosis.
</p>

<p align="center">
  <a href="README.md">简体中文</a> · <a href="README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.3.0-3B82F6?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangGraph-1.2%2B-orange?style=flat-square" alt="LangGraph">
  <img src="https://img.shields.io/badge/MCP-1.0%2B-blueviolet?style=flat-square" alt="MCP">
  <img src="https://img.shields.io/badge/React_18-SPA-61DAFB?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/Kubernetes-Diagnosis-326CE5?style=flat-square&logo=kubernetes" alt="Kubernetes">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Tests-28%2F28_Knowledge_Hub-brightgreen?style=flat-square" alt="Tests">
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#core-capabilities">Capabilities</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#5-minute-demo">Demo</a> •
  <a href="#quick-start">Quick start</a> •
  <a href="#screenshots">Screenshots</a>
</p>

---

## Overview

An enterprise SRE / DevOps platform that turns natural language into infrastructure diagnosis. The Agent plans tool calls across Kubernetes, Docker and SSH, retrieves runbooks from a multi-tenant Knowledge Hub, and writes a structured incident report.

---

## Why AI SRE?

| Dimension | Traditional SRE | This platform |
|-----------|-----------------|---------------|
| Incident response | Alert → bastion → logs (30+ min) | Agent diagnosis in ~20 seconds |
| Tooling | Hand-written kubectl / SSH / Docker | Natural-language planned tool chains |
| Knowledge | Wikis and chat threads | RAG Knowledge Hub |
| Extensibility | Change Agent code for every tool | MCP discovery, no orchestrator rewrite |
| Observability | Split logs / metrics / traces | Agent Trace + SSE + Prometheus |
| Multi-tenancy | Incomplete RBAC | JWT + RBAC + organization isolation |

---

## Core capabilities

### AI SRE Agent

Stateful LangGraph graph: `START → agent → tools → agent → END`. The planner decomposes the incident; reasoning merges tool evidence and runbooks into RCA.

### LangGraph Workflow

The agent node injects RAG and memory, then calls the LLM. The tools node runs builtin and MCP tools in parallel and returns to the agent.

### MCP Tool Ecosystem

Model Context Protocol (stdio) discovers System, Docker, Kubernetes and SSH tools without per-tool Agent changes.

### RAG Knowledge Hub

Uploads, Feishu Wiki sync, and pgvector search. `knowledge_search` is scoped by `organization_id`.

### Kubernetes Diagnosis

CrashLoopBackOff, OOMKilled, ImagePullBackOff, Pending, and 502/503, using pod status, logs, and SOPs.

### Multi Tenant Architecture

Organization isolation, Admin / DevOps / Viewer roles, Fernet-encrypted connector credentials.

### Agent Trace

End-to-end spans for user input, RAG, LLM, and every tool call (args, output, latency) on a waterfall timeline.

### SSE Streaming

Server-Sent Events stream reasoning and tool progress to the Live Execution panel.

---

## Use cases

| Scenario | Example prompt |
|----------|----------------|
| Production 502 | `payment-service 返回大量 502，请分析原因` |
| Pod crash | Inspect CrashLoopBackOff in `production` |
| Connection pool | Diagnose exhausted DB pools |
| Health check | CPU and disk across managed hosts |
| SOP lookup | Standard steps for OOMKilled |

---

## Architecture

```mermaid
flowchart TB
    User([User]) --> Front[React SPA]
    Front --> API[FastAPI REST SSE WebSocket]
    API --> Agent[LangGraph Agent]
    Agent --> LLM[DeepSeek via SiliconFlow]
    Agent --> RAG[RAG Knowledge Hub]
    Agent --> MCP[MCP Client]
    Agent --> Tools[Builtin Tools]
    MCP --> K8s[Kubernetes]
    MCP --> Docker[Docker]
    MCP --> SSH[SSH]
    RAG --> PG[(PostgreSQL pgvector)]
    API --> PG
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

---

## Tech stack

| Layer | Stack |
|-------|--------|
| Agent | LangGraph + LangChain |
| LLM | DeepSeek-V4-Flash (SiliconFlow) |
| API | FastAPI + Uvicorn |
| Knowledge | RAG + pgvector + Feishu connector |
| Tools | MCP + kubectl / Docker / SSH |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Data | PostgreSQL 16 / SQLite (dev) |
| Observability | Agent Trace, SSE, Prometheus, Grafana |
| Deploy | Docker Compose |

---

## 5-minute Demo

Production Kubernetes: `payment-service` returning HTTP 502.

1. Sign in (`/login`).
2. Open Copilot (`/ops`) and enter:

```text
payment-service 返回大量 502，请分析原因
```

3. The Agent calls:

- `kubectl_get_pods`
- `kubectl_logs`
- `knowledge_search`
- `system_logs`

4. Output:

- Root Cause Analysis
- Incident Timeline
- Solution Recommendation

Load demo knowledge:

```bash
python demo/import_demo_data.py
```

Scenario files: [demo/](demo/) and [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

---

## Screenshots

| Dashboard | Agent Chat |
|-----------|------------|
| ![Dashboard](screenshots/01-dashboard.png) | ![Agent Chat](screenshots/02-agent-chat.png) |

| Knowledge Hub | Trace Viewer |
|---------------|--------------|
| ![Knowledge Hub](screenshots/03-knowledge-hub.png) | ![Trace](screenshots/04-trace-viewer.png) |

| Kubernetes | Incident Report |
|------------|-----------------|
| ![Kubernetes](screenshots/05-kubernetes.png) | ![Incident Report](screenshots/06-incident-report.png) |

![Architecture](screenshots/07-architecture.png)

---

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 18+ (local frontend)
- Docker (optional)
- [SiliconFlow](https://cloud.siliconflow.cn) API key

### Docker

```bash
git clone https://github.com/zhifengjin050-arch/enterprise-ai-sre-platform.git
cd enterprise-ai-sre-platform
cp .env.example .env
# Set SILICONFLOW_API_KEY in .env
docker compose up -d
```

Open http://localhost and register.

### Local development

**Backend**

```bash
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Dev UI: http://localhost:5173 (proxies `/api` to port `8000`).

### Console routes

| Route | Page |
|-------|------|
| `/overview` | Dashboard |
| `/ops` | AI SRE Copilot |
| `/infra` | Hosts / Docker / Kubernetes |
| `/knowledge` | Knowledge Hub |
| `/traces` | Agent Trace |
| `/incidents` | Incidents |
| `/monitor` | Monitoring |

---

## Roadmap

### v3.3.0 (current)

- [x] LangGraph Agent, MCP, RAG Knowledge Hub
- [x] Kubernetes diagnosis, multi-tenancy, Trace, SSE
- [x] Demo pack and open-source docs

### v3.4 (Planned)

- Multi Cloud Intelligence
- Autonomous Repair Workflow
- MCP Ecosystem

---

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Demo guide](docs/DEMO_GUIDE.md)
- [Interview guide](docs/INTERVIEW_GUIDE.md)
- [Release notes](docs/V3.3_RELEASE_NOTES.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)

---

## GitHub

https://github.com/zhifengjin050-arch/enterprise-ai-sre-platform

---

## License

[MIT](LICENSE) © 2026 Enterprise AI SRE Platform
