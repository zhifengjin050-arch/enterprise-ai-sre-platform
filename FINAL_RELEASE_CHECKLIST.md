# Final Release Checklist — v3.3.0

Use this list immediately before pushing the public GitHub repository.

## Code

- [ ] `pytest tests/test_v33_knowledge_hub.py -q` → 28 passed
- [ ] No changes to Agent / RAG / MCP / Auth core logic
- [ ] `frontend/package.json` version is `3.3.0`

## Docker / local run

- [ ] `.env.example` exists and does not contain real secrets
- [ ] README includes `cp .env.example .env` before `docker compose up -d`
- [ ] Local backend command documented: `uvicorn app.main:app`
- [ ] Local frontend commands documented: `npm install` / `npm run dev`

## Secrets

- [ ] `.env` is gitignored and not tracked
- [ ] No live API keys, passwords, kubeconfig, or private keys in git
- [ ] Historical key fragments redacted

## Docs

- [ ] `README.md` (zh) and `README_EN.md` (en)
- [ ] `LICENSE` (MIT)
- [ ] `CONTRIBUTING.md`
- [ ] `SECURITY.md`
- [ ] `CHANGELOG.md` has v3.3.0
- [ ] `docs/` contains architecture, demo, interview, and release notes

## Screenshots

- [ ] `screenshots/01-dashboard.png`
- [ ] `screenshots/02-agent-chat.png`
- [ ] `screenshots/03-knowledge-hub.png`
- [ ] `screenshots/04-trace-viewer.png`
- [ ] `screenshots/05-kubernetes.png`
- [ ] `screenshots/06-incident-report.png`
- [ ] `screenshots/07-architecture.png`

## Git / GitHub

- [ ] Working tree clean (`git status`)
- [ ] Default branch `main`
- [ ] Tag `v3.3.0`
- [ ] Public repo `enterprise-ai-sre-platform`
- [ ] Description and Topics set
- [ ] GitHub Release `v3.3.0 Enterprise Knowledge Hub`
