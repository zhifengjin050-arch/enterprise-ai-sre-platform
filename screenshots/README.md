# Screenshots

Captured from the real React console (`frontend/src`) with Playwright. Do not replace with stock or AI-generated placeholders.

| File | Route | Content |
|------|-------|---------|
| `01-dashboard.png` | `/overview` | Executive dashboard |
| `02-agent-chat.png` | `/ops` | 502 diagnosis conversation |
| `03-knowledge-hub.png` | `/knowledge` | Knowledge sources / RAG |
| `04-trace-viewer.png` | `/traces` | Tool-calling waterfall |
| `05-kubernetes.png` | `/infra` Kubernetes tab | Cluster / pod view |
| `06-incident-report.png` | `/ops` | Generated incident report |
| `07-architecture.png` | Mermaid render | System architecture |

Regenerate:

```bash
cd frontend
npm install
npx --yes playwright@1.49.1 install chromium
node ../scripts/capture_screenshots.mjs
```
