# FINAL v3.2.0 Debug Acceptance

> Generated: 2026-08-18T01:00:06Z
> MCP 隔离子进程复测: 2026-08-18T01:03:53Z
> Base: http://127.0.0.1:8000 · Front: http://127.0.0.1:5173
> 脚本: `scripts/v3.2_debug_acceptance.py`

## 汇总

| 批次 | Total | Passed | Failed | Pass rate |
|------|-------|--------|--------|-----------|
| 全量脚本（含 MCP 脚本缺陷） | 57 | 55 | 2 | 96% |
| MCP `mcp-probe` 修复后 | 57 | 57 | 0 | **100%**（MCP 两项改为复测 PASS） |

失败项根因是验收脚本把 `def mcp_probe` 写丢（`NameError`），**不是** MCP Server 崩溃。复测 JSON：`connected=true, tool_count=17`，三工具均 `ok`（docker/k8s 为结构化 error）。

## 评分（真实运行）

| 维度 | 评分 | 依据 |
|------|------|------|
| Backend | 95/100 | 18/18 API 探活通过；SQLite 开发模式 |
| Frontend | 92/100 | 8 路由 SPA 200、vitest、production build；无头未采 console |
| Agent | 95/100 | Chat 200 + 工具调用 + Trace + SSE complete |
| RAG | 95/100 | upload/search/Agent 引用 SOP |
| Memory | 90/100 | 同 conversation_id 两轮；第二轮接「之前」 |
| MCP | 90/100 | 17 工具已发现；无 Docker/K8s 时结构化错误 |
| Security | 70/100 | 未认证 401 正确；JWT 弱密钥仅 dev |
| Production | 55/100 | Redis/PG/Grafana 未起 |

## Enterprise Demo Ready

**YES — 本地 Enterprise Demo Ready**（`webtest` 登录 + Overview + Copilot/Chat + RAG + Trace + MCP System 工具）。

未达 Production Ready：弱 JWT、无 Redis/PG、无 Grafana、Docker/K8s 本机未装。

## 本轮修改（明确 Bug，无架构重构）

| 文件 | 修改原因 | 影响范围 |
|------|----------|----------|
| `frontend/tsconfig.json` | `tsc` TS2550 replaceAll / lib ES2020 | 仅类型检查 |
| `frontend/src/features/incidents/Incidents.tsx` | 标题硬编码英文 | 事件页 i18n |
| `frontend/src/features/knowledge/KnowledgeCenter.tsx` | 同上 | 知识库页 i18n |
| `frontend/src/features/infra/InfraExplorer.tsx` | 同上 | 基础设施页 i18n |
| `app/main.py` | 删除重复 `include_router(repair_router)` | OpenAPI 去重，行为不变 |
| `scripts/v3.2_debug_acceptance.py` | SSE 整包解析、MCP utf-8、Vision≥28px、恢复 `mcp_probe` | 仅验收 |

调试探针仍保留在 `app/agent/agent.py`、`app/mcp/manager.py`、`app/main.py` chat、`Overview.tsx`（确认无问题后可删除）。

## Phase 6 代码质量摘要

- FastAPI：路由齐全；repair 重复注册已删。
- Chat：`run_in_threadpool`；SSE 用队列 + heartbeat。
- `observe_llm_request` 仍只 `except ImportError`；本轮未再触发 NameError。
- Pydantic ChatRequest / 知识库 schema 与实测 JSON 一致。
- React：Overview 失败走 fallback，不把 `t` 放入 fetch 依赖。
- 未做全量 unused 清扫（约束：不改核心业务）。
