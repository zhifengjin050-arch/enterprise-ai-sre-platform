# 项目2 MCP Server 审计报告

> Enterprise DevOps MCP Server v1.0.1  
> 路径：`d:\代码项目\AI Agent项目\项目2：Enterprise DevOps MCP Server`

---

## 1. 定位

独立 **DevOps Tool Provider**，通过 MCP 协议向 AI Agent（Cursor / Claude / 项目1 Client）暴露运维工具。  
项目1 **不复制** 其业务代码，仅通过标准 MCP Client 调用。

---

## 2. 启动方式

| 方式 | 命令 |
|------|------|
| 推荐 | `python scripts/run_devops_mcp.py`（cwd=项目根） |
| 模块 | `python -m app.server` |
| Docker | `ENTRYPOINT ["python", "-m", "app.server"]`（仍为 stdio） |

入口：`app/server.py` → `init_server()` → `mcp.run(show_banner=False)`

**传输：stdio only**（无 HTTP/SSE 业务端口）。  
stdout 专供 MCP JSON-RPC；日志全部写 stderr。

---

## 3. 协议实现

| 项 | 结论 |
|----|------|
| SDK | FastMCP（`fastmcp>=2.0`） |
| 传输 | stdio |
| 工具注册 | `@mcp.tool` + `register_all_tools(mcp)` |
| 权限 | `@require_permission` / 执行类需 `EXECUTE_TOOLS_ENABLED` |

---

## 4. 已支持工具（17）

### System（7）

`get_server_health`, `get_system_info`, `get_cpu_usage`, `get_memory_usage`, `get_disk_usage`, `list_processes`, `get_audit_logs`

### Docker（3）

`docker_list`, `docker_logs`, `docker_restart`（执行类）

### Kubernetes（4）

`k8s_get_pods`, `k8s_get_deployments`, `k8s_get_services`, `k8s_logs`

### SSH（3）

`ssh_check_connection`, `ssh_execute_command`（执行类）, `ssh_upload_file`（执行类）

---

## 5. 参数与返回格式

- 参数：JSON object（FastMCP / MCP `inputSchema`）
- 成功：结构化 dict，经 MCP content 序列化（常为 JSON text）
- 失败 / 权限拒绝：`{"error": "...", ...}` 或 `{status:"error", message}`

---

## 6. 关键配置

`ALLOWED_TOOLS`, `EXECUTE_TOOLS_ENABLED`（默认 false）, `K8S_*`, `SSH_*`, `BLOCKED_COMMANDS`, `AUDIT_LOG_*`, `FASTMCP_SHOW_SERVER_BANNER=false`

---

## 7. 与项目1的集成方式

项目1 以 **stdio MCP Client** 方式：

```
spawn: MCP_SERVER_COMMAND + ARGS
cwd:   MCP_SERVER_CWD = 项目2 根目录
```

示例：

```
ENABLE_MCP=true
MCP_SERVER_COMMAND=python
MCP_SERVER_ARGS=-m,app.server
MCP_SERVER_CWD=d:\代码项目\AI Agent项目\项目2：Enterprise DevOps MCP Server
MCP_TIMEOUT=30
```

项目2 保持独立进程；项目1 不修改、不 vendoring 项目2 源码。
