# MCP Demo：订单系统故障诊断

> Enterprise AI DevOps Platform v2.0 + Enterprise DevOps MCP Server  
> 前置：`ENABLE_MCP=true` 且 `MCP_SERVER_CWD` 指向项目2根目录

---

## Demo1 — 检查订单系统是否正常

### 用户输入

```
检查订单系统是否正常
```

### 期望 Agent 流程

```
用户问题
    ↓
Agent 分析（LangGraph agent_node）
    ↓
调用 MCP 工具：k8s_get_pods
    ↓
发现：order-service Pod 状态异常 / restart 次数高
    ↓
调用 MCP 工具：k8s_logs（pod_name=order-service）
    ↓
发现：OOMKilled / CrashLoopBackOff 相关日志
    ↓
查询 RAG 知识库（OOM / CrashLoop SOP）
    ↓
结合 Memory（历史同类故障）
    ↓
生成故障分析报告
```

### 期望工具调用（MCP）

| 顺序 | 工具 | 参数示例 |
|:----:|------|----------|
| 1 | `k8s_get_pods` | `namespace=default` |
| 2 | `k8s_logs` | `pod_name=order-service`, `lines=100` |
| 可选 | `docker_list` / `get_server_health` | 补充主机/容器视角 |

### 期望报告要素

1. **现象**：Pod 重启 / 状态异常  
2. **证据**：日志中的 OOMKilled 或 CrashLoopBackOff  
3. **根因**：内存 limit 过小 / 泄漏 / 流量突增（结合 RAG）  
4. **修复建议**：调整 memory limit、排查泄漏、滚动重启（若允许）  
5. **SOP 引用**：知识库中 OOM 处理步骤  

### 演示话术（面试 / 产品）

> 「用户用自然语言提问后，Agent 不会写死脚本，而是通过 MCP Client 动态发现项目2暴露的 `k8s_get_pods`、`k8s_logs` 等工具，拉起独立 MCP Server 子进程执行，再把结果与 RAG 知识库融合，输出可落地的故障报告。关闭 `ENABLE_MCP` 时仍可回退到平台内置工具，保证兼容。」

---

## Demo2 — 服务器健康巡检（MCP System）

### 用户输入

```
帮我检查生产服务器健康状态
```

### 期望 MCP 工具

- `get_server_health` 或 `get_cpu_usage` / `get_memory_usage` / `get_disk_usage`

### 期望输出

CPU / Memory / Disk 指标 + 风险等级 + 建议

---

## Demo3 — Docker 容器检查

### 用户输入

```
检查订单服务容器状态
```

### 期望 MCP 工具

- `docker_list`
- `docker_logs`（如发现异常容器）

---

## 启动检查清单

- [ ] 项目2可独立运行：`python -m app.server`（stdio）
- [ ] 项目1 `.env`：`ENABLE_MCP=true` + 正确 `MCP_SERVER_CWD`
- [ ] `GET /api/agent/stats` → `tool_stats.mcp.connected == true`
- [ ] Chat 轨迹中出现 MCP 工具名
