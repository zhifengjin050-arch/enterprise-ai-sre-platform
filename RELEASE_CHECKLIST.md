# Release Checklist — v3.3.0 Enterprise Knowledge Hub

> **目标版本**: `v3.3.0`  
> **检查日期**: ________________  
> **负责人**: ________________  
> **状态**: □ 未开始  □ 进行中  □ **就绪可发布**

---

## 1. 代码检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 1.1 | pytest 全部通过 | `pytest tests/test_v33_knowledge_hub.py -v` → 28 passed ✅ | □ | |
| 1.2 | 全量测试通过 | `pytest` 或核心测试 → 280+ passed ✅ | □ | |
| 1.3 | 无 Pending 迁移 | `alembic check` → "No new migrations" | □ | |
| 1.4 | 迁移可回滚 | `alembic downgrade -1` → 成功，再 `alembic upgrade head` | □ | |
| 1.5 | 代码无敏感信息 | `git diff --cached` 检查无 `.env`、无硬编码密钥、无 `change-me` | □ | |
| 1.6 | 代码风格合规 | `ruff check app/` 或等效工具 | □ | |
| 1.7 | 类型检查 | `mypy app/ --ignore-missing-imports` | □ | (可选) |

---

## 2. Docker 检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 2.1 | Docker Compose 配置有效 | `docker compose config` → 语法正确 | □ | |
| 2.2 | 一键启动正常 | `docker compose up -d` → 所有服务 healthy | □ | |
| 2.3 | 生产配置有效 | `docker compose -f docker-compose.prod.yml config` → 语法正确 | □ | |
| 2.4 | 前端构建成功 | `docker compose build frontend` 或 `cd frontend && npx vite build` | □ | |
| 2.5 | 后端健康检查 | `curl http://localhost:8000/health` → `{"status":"healthy"}` | □ | |
| 2.6 | 无端口冲突 | Docker 服务端口未被占用 | □ | |

---

## 3. 数据库检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 3.1 | 迁移历史完整 | `alembic history` → 线性历史无分叉 | □ | |
| 3.2 | 所有表已创建 | 检查 `users`, `organizations`, `documents`, `document_chunks`, `agent_executions`, `conversations`, `knowledge_sources`, `knowledge_documents`, `knowledge_chunks`, `sync_tasks`, `sync_logs` | □ | |
| 3.3 | 新表可读写 | 创建 KnowledgeSource → 查询 → 删除 | □ | |
| 3.4 | SQLite / PostgreSQL 兼容 | 两种数据库下 Alembic 迁移均成功 | □ | |

---

## 4. 前端检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 4.1 | 所有页面可访问 | `/overview`, `/ops`, `/infra`, `/incidents`, `/knowledge`, `/traces`, `/monitor` → 200 | □ | |
| 4.2 | 知识 Hub 页面正常 | `/knowledge` → 标签页切换、文档列表、搜索正常 | □ | |
| 4.3 | AI Copilot 正常 | `/ops` → SSE 流式对话、Markdown 渲染、Live Execution 面板 | □ | |
| 4.4 | 旧路由可跳转 | `/chat`, `/dashboard`, `/servers`, `/kubernetes` → 重定向到新路径 | □ | |
| 4.5 | 移动端适配 | 侧边栏折叠、布局响应式 | □ | (可选) |
| 4.6 | 前端无控制台错误 | 打开 DevTools Console → 无 Error/警告 | □ | |

---

## 5. Demo 流程检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 5.1 | 注册/登录 | 新用户注册 → JWT Token → 自动登录 → Dashboard 展示 | □ | |
| 5.2 | Demo 数据导入 | `python demo/import_demo_data.py` → 3 文档上传成功 | □ | |
| 5.3 | 知识库语义搜索 | `/knowledge` 搜索 "OOMKilled" → 命中 K8s 故障手册 | □ | |
| 5.4 | 502 故障诊断 Demo | `/ops` 输入 "生产环境 payment-service 出现大量 502" → Agent 完成完整诊断 | □ | |
| 5.5 | 故障报告输出 | Agent 输出包含: 问题摘要、影响范围、根因分析、诊断证据、处理方案 | □ | |
| 5.6 | Agent Trace | `/traces` 可看到上一步执行记录、工具调用可追溯 | □ | |

---

## 6. 文档检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 6.1 | README.md | 版本号 v3.3.0、Features、Architecture、Demo、快速开始完整 | □ | |
| 6.2 | ARCHITECTURE.md | 架构分层、Agent 引擎、知识库、安全、部署完整 | □ | |
| 6.3 | DEMO_GUIDE.md | 5 分钟 Demo 流程、面试场景剧本、故障排查自检 | □ | |
| 6.4 | V3.3_RELEASE_NOTES.md | 新功能、改进、Bug 修复、已知问题、升级指南 | □ | |
| 6.5 | V3.3_FINAL_AUDIT.md | 审计结果、已知发现、修复建议 | □ | |
| 6.6 | demo/README.md | 数据说明、快速开始、预期效果 | □ | |
| 6.7 | .env.example | 环境变量完整、注释清晰 | □ | |
| 6.8 | 截图就绪 | `docs/images/` 包含关键页面截图 | □ | (部署后截图) |

---

## 7. 版本与标签

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 7.1 | 版本号一致性 | 搜索代码中所有 `3.2` 或 `3.2.1`，确认已更新为 `3.3.0` | □ | |
| 7.2 | Git Tag | `git tag v3.3.0` → 推送到远程 | □ | |
| 7.3 | CHANGELOG 更新 | `CHANGELOG.md` 包含 v3.3.0 条目 | □ | |
| 7.4 | GitHub Release 创建 | `gh release create v3.3.0` → 标题、描述、附件 | □ | |

---

## 8. 安全检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 8.1 | JWT 密钥足够强 | 生产使用 `openssl rand -hex 32` | □ | |
| 8.2 | 无密钥硬编码 | `rg "sk-|change-me|password" --include="*.py" --include="*.ts" --include="*.tsx"` | □ | |
| 8.3 | .env 在 .gitignore 中 | `.env` 不会被提交到 Git | □ | |
| 8.4 | CORS 生产配置 | `docker-compose.prod.yml` 中 CORS 为空或白名单 | □ | |
| 8.5 | 日志无敏感信息泄露 | `SecretFilter` 对 API Key / JWT / DB 密码脱敏 | □ | |

---

## 9. 最终检查

| # | 检查项 | 标准 | 状态 | 备注 |
|---|--------|------|------|------|
| 9.1 | Release 名称与版本 | "Enterprise AI SRE Platform v3.3.0 Enterprise Knowledge Hub" | □ | |
| 9.2 | Release 附件 | 包含源码 tar.gz + Release Notes | □ | |
| 9.3 | 面试准备 | Demo 流程可 5 分钟内完整演示 | □ | |
| 9.4 | README 截图 | 项目截图已放入 `docs/images/` 并更新 README | □ | (部署后) |

---

## 签署

| 角色 | 姓名 | 日期 | 签名 |
|------|------|------|------|
| **开发负责人** | ________________ | ________________ | ________ |
| **测试负责人** | ________________ | ________________ | ________ |
| **发布经理** | ________________ | ________________ | ________ |

---

## 快速命令参考

```bash
# 测试
pytest tests/test_v33_knowledge_hub.py -v
pytest

# 数据库迁移
alembic check
alembic upgrade head

# Docker
docker compose config
docker compose up -d
docker compose ps

# Demo 导入
python demo/import_demo_data.py

# 安全扫描
python scripts/security_check.py

# Git Tag
git tag -a v3.3.0 -m "Enterprise Knowledge Hub Release"
git push origin v3.3.0
```

---

> **文档版本**: v3.3.0 | **更新日期**: 2026-08-18 | **返回**: [README](./README.md)