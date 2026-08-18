# 订单服务 502 故障 — Agent 自动恢复 Demo

> 版本：Enterprise AI DevOps Platform v3.1.0  
> 场景：生产订单服务 HTTP 502，AI SRE 完成诊断 → 审批 → 执行 → Trace

截图建议存放：`docs/images/demo-order-502-trace.png`（Agent Trace 页）  
相关页面：`/chat`、`/trace`

---

## 用户输入

```
生产订单服务502，请自动分析
```

---

## Agent 思考流程

```
用户请求
  → Agent 分析意图（生产故障 / 订单服务 / 502）
  → RAG 检索「订单 502 SOP」
  → Memory 查询历史同类案例
  → MCP 查询 K8s / 日志
  → 生成修复方案（restart deployment）
  → 因 docker_restart / k8s restart 为 dangerous，进入 Approval
  → 用户确认
  → MCP 执行重启
  → 写入 Trace + Memory
```

---

## 逐步调用链

### Step 1 — 查询 Kubernetes 状态

| 项 | 值 |
|----|----|
| 工具 | `k8s_get_pods` / `k8s_get_deployments` |
| 元数据 | risk=`safe`，permission=`devops.viewer`，audit=`false` |
| 预期发现 | `order-service` Pod `CrashLoopBackOff` 或 Ready=0/1 |

### Step 2 — 发现 Pod 异常

Agent 将状态归纳为：订单 Deployment 副本不健康，Ingress 返回 502。

### Step 3 — 读取日志

| 项 | 值 |
|----|----|
| 工具 | `k8s_logs`（或 `docker_logs`） |
| 风险 | safe |
| 关注点 | OOMKilled / 连接池耗尽 / 上游超时 |

### Step 4 — RAG 查询故障 SOP

检索知识库文档（示例已用于验收上传）：

- 查 Ingress / Service 后端
- 查 Pod Ready
- 读日志
- 必要时重启 Deployment

### Step 5 — Memory 查询历史案例

读取近期 `agent_executions` / 会话消息，若存在「订单 OOM / 502」历史，则引用当时方案。

### Step 6 — 生成修复方案

```markdown
## AI 自动修复方案
| # | 操作 | 安全级别 | 需要确认 |
|---|------|----------|----------|
| 1 | 滚动重启 order-service | dangerous | 需确认 |
```

对应 MCP 工具示例：`docker_restart` 或 `kubectl_restart_deployment`  
元数据：`risk_level=dangerous`，`required_permission=devops.admin`，`audit_required=true`

### Step 7 — Approval

用户发送：

```
确认修复 <token>
```

或调用：

```
POST /api/repair/approve  { "token": "<token>" }
```

系统拒绝自动执行删除库、删文件、改生产配置等操作。

### Step 8 — MCP 执行 restart

审批通过后调用工具，结果写入 `AgentTrace`（`event_type=auto_repair`）。

---

## 最终结果（示例）

1. 根因：订单 Pod 反复重启，上游网关 502。  
2. 处置：人工确认后重启工作负载。  
3. 验证：再次 `k8s_get_pods`，Ready=1/1。  
4. Trace：可在 `/trace?conversation_id=<id>` 回放全链路。

## 运行命令

```bash
# 开发
uvicorn app.main:app --reload --port 8000

# 对话
# POST /api/chat  {"message":"生产订单服务502，请自动分析"}
```
