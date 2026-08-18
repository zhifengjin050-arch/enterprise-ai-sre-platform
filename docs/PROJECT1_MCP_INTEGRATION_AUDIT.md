# 项目1 MCP 集成审计报告

> Enterprise AI DevOps Platform v1.3.0 → v2.0 MCP Client 接入前审计  
> 性质：只读分析，不修改业务代码（本阶段）

---

## 1. 当前 Agent 执行流程

```
用户请求 (POST /api/chat | WS /ws/chat)
    ↓
_run_agent / WebSocket handler
    ↓
LangGraph: START → agent → (pending tool_calls?) → tools → agent → … → END
```

关键文件：

| 角色 | 路径 |
|------|------|
| 图编排 | `app/agent/graph.py` |
| Agent 节点 | `app/agent/agent.py` |
| Tools 节点 | `app/agent/tools_node.py` |
| 状态 | `app/agent/state.py` |
| 入口 | `app/main.py` (`_agent_graph` 模块级单例) |

Tool Calling 为手写 Function Calling（`DeepSeekClient.chat_with_tools`），**未**使用 LangChain `bind_tools` / 官方 `ToolNode`。

---

## 2. 当前工具系统设计

### 结构

```
app/tools/
  registry.py          # 注册中心
  server_health.py
  docker_ops.py
  logs.py
  k8s_ops.py
  ssh_ops.py
app/agent/k8s_tools.py # 也被 registry 加载
```

### 注册方式

`registry._load_tools()` 扫描模块中带 `.name` / `.func` 的 LangChain `@tool` 对象，惰性缓存到 `_tool_registry`。

### API

- `get_tool(name)` — 执行查找
- `get_all_tools()` — 列表
- `get_tool_schemas()` — OpenAI Function Calling schema

### 内置工具（18）

`server_health`, `docker_status`, `docker_logs`, `system_logs`, `k8s_pods`, `k8s_deployments`, `k8s_services`, `k8s_pod_logs`, `kubectl_get_pods`, `kubectl_get_nodes`, `kubectl_logs`, `kubectl_describe_pod`, `kubectl_restart_deployment`, `ssh_exec`, `ssh_server_health`, `ssh_docker_status`, `ssh_docker_logs`, `ssh_system_logs`

---

## 3. MCP 接入点

| 接入点 | 说明 |
|--------|------|
| `get_tool_schemas()` | 合并 MCP tools 的 schema 供 LLM 选择 |
| `get_tool(name)` | Tool Router：MCP 优先，再回退内置 |
| `tools_node` | 统一 `.invoke(args)`，MCP 包装成同构对象 |
| `on_startup` / `on_shutdown` | MCP Client 生命周期 |
| `app/config.py` | `ENABLE_MCP` 及 stdio 启动参数 |

---

## 4. 需要修改的文件

| 文件 | 改动 |
|------|------|
| **新建 `app/mcp/`** | client / manager / tools / config |
| `app/tools/registry.py` | 合并 internal + MCP |
| `app/agent/agent.py` | 去掉 schema 闭包缓存，每次刷新 |
| `app/agent/prompts.py` | 工具清单改为动态说明 |
| `app/main.py` | lifespan 启停 MCP；stats 报告 MCP 状态 |
| `app/config.py` / `.env.example` | MCP 环境变量 |
| `requirements.txt` | 增加 `mcp` SDK |
| 内置 `app/tools/*.py` | **不改业务实现** |

---

## 5. RAG / Memory（保持不变）

- RAG：`agent_node` 内 `retrieve_knowledge` → 注入 system prompt
- 长期记忆：`get_recent_failures` / `get_successful_solutions`
- 短期记忆：`load_conversation_history` 已实现但主链路未接线（非本次范围）

---

## 6. 风险分析

| 风险 | 级别 | 缓解 |
|------|:----:|------|
| `agent_node` 启动时缓存 `tool_schemas` | 高 | 每次调用 `get_tool_schemas()` |
| 图模块级单例 | 中 | registry 动态合并即可，不必重建图 |
| MCP 连接失败阻断启动 | 中 | 失败降级到内置工具 |
| 工具名冲突 | 中 | ENABLE_MCP 时 MCP 同名覆盖 |
| 同步 FastAPI + 异步 MCP SDK | 中 | 专用事件循环/线程桥接 |
| Windows 路径 / CWD 配置错误 | 中 | `.env.example` 写清项目2路径 |

---

## 7. 结论

项目1 架构清晰，registry 是唯一聚合点，适合以 **stdio MCP Client** 方式接入项目2，且可在 `ENABLE_MCP=false` 时保持 v1.3.0 行为完全兼容。
