<div align="center">

# Enterprise AI DevOps Platform

**An enterprise SRE Agent platform: MCP tool calling, RAG knowledge hub, memory, and cloud-native diagnosis.**

Turn natural-language incidents into planned tool chains, retrieved runbooks, and structured incident reports.

[中文](README.md) · [Architecture](docs/ARCHITECTURE.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

[![Version](https://img.shields.io/badge/Version-v3.3.0-3B82F6)]()
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent-orange)]()
[![MCP](https://img.shields.io/badge/MCP-Tool_Calling-8A2BE2)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## Positioning

Not a chatbot wrapper. An **enterprise operations product** for SRE and platform teams:

- **AI Agent** — LangGraph planner over live infrastructure evidence
- **MCP Tool Calling** — Kubernetes / Docker / SSH without rewriting the orchestrator
- **RAG Knowledge Hub** — multi-tenant runbooks and SOP retrieval
- **Memory** — working memory across a diagnosis session
- **Multi-tenant** — JWT, RBAC, organization isolation
- **Docker / Kubernetes** — Compose to run the platform; K8s as a diagnosis target

Repo: [enterprise-ai-sre-platform](https://github.com/zhifengjin050-arch/enterprise-ai-sre-platform)

---

## Demo

<video controls playsinline width="100%" poster="docs/videos/cover.png" preload="metadata">
  <source src="https://cdn.jsdelivr.net/gh/zhifengjin050-arch/enterprise-ai-sre-platform@main/docs/videos/demo.mp4" type="video/mp4" />
</video>

[![Demo video](docs/videos/cover.png)](https://zhifengjin050-arch.github.io/enterprise-ai-sre-platform/)

Click the cover to watch the walkthrough (Chinese narration + subtitles). GitHub file pages do not play repo mp4s, so the player is hosted on GitHub Pages.

---

## Features

- Stateful Agent graph: `START → agent → tools → agent → END`
- MCP discovery for System / Docker / Kubernetes / SSH
- cosine RAG scoped by `organization_id`
- CrashLoopBackOff, OOMKilled, ImagePullBackOff, 502/503 playbooks
- Agent Trace + SSE live execution
- Incident reports with cited runbooks

---

## Architecture

<img src="screenshots/07-architecture.png" alt="System architecture" width="100%" />

```mermaid
flowchart TB
    User([SRE / DevOps]) --> UI[React Dashboard]
    UI --> API[FastAPI Gateway]
    API --> Agent[LangGraph Agent Runtime]
    Agent --> Mem[Memory]
    Agent --> RAG[RAG Knowledge Hub]
    Agent --> MCP[MCP Tool Calling]
    MCP --> K8s[Kubernetes]
    MCP --> Docker[Docker]
    MCP --> SSH[SSH]
    RAG --> PG[(PostgreSQL + embeddings)]
    API -.-> JWT[JWT / RBAC / Org isolation]
```

### Agent workflow

```mermaid
flowchart LR
    Q[Incident query] --> P[Planner]
    P --> T[Tool calling]
    T --> R[RAG / Memory]
    R --> L[LLM reasoning]
    L --> I[Incident Report]
```

---

## Use cases

| Scenario | Example |
|----------|---------|
| Production 502 | `payment-service is returning 502, find the root cause` |
| Pod crash | `CrashLoopBackOff in production namespace` |
| Capacity | `database connection pool is exhausted` |
| Fleet check | `inspect CPU and disk on managed hosts` |
| SOP lookup | `standard steps for OOMKilled` |

---

## Tech Stack

Python 3.12 · FastAPI · LangGraph · MCP · PostgreSQL · React 18 · Docker Compose · Prometheus / Grafana

---

## Screenshots

| Dashboard | Agent interaction |
|-----------|-------------------|
| ![Dashboard](screenshots/01-dashboard.png) | ![Agent](screenshots/02-agent-chat.png) |

| Kubernetes | Architecture |
|------------|--------------|
| ![Kubernetes](screenshots/05-kubernetes.png) | ![Architecture](screenshots/07-architecture.png) |

---

## Quick Start

```bash
git clone https://github.com/zhifengjin050-arch/enterprise-ai-sre-platform.git
cd enterprise-ai-sre-platform
cp .env.example .env
docker compose up -d
```

Open http://localhost · `python demo/import_demo_data.py` for sample knowledge.

---

## Deployment

`docker compose up -d` is the supported path. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Never commit a real `.env`.

---

## Roadmap

**v3.3.0 (current):** Agent, MCP, RAG, multi-tenant, Trace, SSE, Docker.

Later: multi-cloud intelligence, autonomous repair, larger MCP catalog.

---

## License

[MIT](LICENSE) · [CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)
