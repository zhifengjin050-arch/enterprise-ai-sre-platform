# GitHub Release — v3.3.0

## Initial public showcase

Enterprise AI DevOps Platform (AI SRE Agent) — first GitHub-ready packaging of the v3.3.0 product line.

## Core Features

- LangGraph AI Agent (`START → agent → tools → agent → END`)
- MCP tool calling (Kubernetes / Docker / SSH)
- RAG Knowledge Hub with multi-tenant isolation
- Memory, Agent Trace, SSE live execution
- Docker Compose runtime

## Deployment Support

```bash
cp .env.example .env
docker compose up -d
```

See README.md and docs/DEPLOYMENT.md.
