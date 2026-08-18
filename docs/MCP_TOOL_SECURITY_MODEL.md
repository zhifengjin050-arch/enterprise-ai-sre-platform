# MCP Tool Security Model

> Enterprise AI DevOps Platform v3.1.0  
> 原则：**不修改既有工具执行逻辑**，仅增加元数据供 Agent 安全决策。

---

## 设计

```
Agent / Approval
    ↓
Tool Metadata (name, risk_level, required_permission, audit_required)
    ↓
Tool Router → MCP Client → Project2 MCP Server（原工具实现不变）
```

实现位置：

| 项目 | 文件 | 说明 |
|------|------|------|
| 项目1 | `app/mcp/metadata.py` | Agent 侧查询与审批 |
| 项目2 | `app/tools/metadata.py` | Server 侧目录，不改 `docker.py` / `system.py` 等 |

`MCPToolWrapper` 在包装时附加 `metadata` 字段，`invoke()` 行为不变。

---

## 字段

| 字段 | 说明 |
|------|------|
| name | 工具名 |
| description | 用途 |
| category | system / docker / kubernetes / ssh |
| risk_level | `safe` / `moderate` / `dangerous` |
| required_permission | `devops.viewer` / `devops.admin` |
| audit_required | 是否必须审计 / 审批 |

---

## 目录（Project2 17 Tools）

| name | category | risk_level | required_permission | audit_required |
|------|----------|------------|---------------------|----------------|
| get_server_health | system | safe | devops.viewer | false |
| get_system_info | system | safe | devops.viewer | false |
| get_cpu_usage | system | safe | devops.viewer | false |
| get_memory_usage | system | safe | devops.viewer | false |
| get_disk_usage | system | safe | devops.viewer | false |
| list_processes | system | safe | devops.viewer | false |
| get_audit_logs | system | moderate | devops.admin | true |
| docker_list | docker | safe | devops.viewer | false |
| docker_logs | docker | safe | devops.viewer | false |
| **docker_restart** | docker | **dangerous** | **devops.admin** | **true** |
| k8s_get_pods | kubernetes | safe | devops.viewer | false |
| k8s_get_deployments | kubernetes | safe | devops.viewer | false |
| k8s_get_services | kubernetes | safe | devops.viewer | false |
| k8s_logs | kubernetes | safe | devops.viewer | false |
| ssh_check_connection | ssh | safe | devops.viewer | false |
| ssh_execute_command | ssh | dangerous | devops.admin | true |
| ssh_upload_file | ssh | dangerous | devops.admin | true |

### 示例

**docker_restart**

```yaml
name: docker_restart
risk_level: dangerous
required_permission: devops.admin
audit_required: true
```

**get_cpu_usage**

```yaml
name: get_cpu_usage
risk_level: safe
audit_required: false
```

---

## Agent 决策

1. `classify_tool(name)` 优先读 Metadata。  
2. `dangerous` 必须走 Approval。  
3. 禁止自动：删库、删文件、改生产配置。
