# Enterprise AI DevOps Agent — 演示场景

> 本文档包含 4 个标准演示场景，用于面试展示、技术评审和项目验收。
> 每个场景展示 AI Agent 的核心能力：自然语言理解 → 工具调用 → 数据分析 → 报告生成。

---

## Demo 1：生产服务器巡检

### 目标
展示 AI Agent 自动巡检多台生产服务器并生成巡检报告的能力。

### 用户输入

```
检查生产环境所有服务器的健康状态
```

### Agent 思考流程

```
1. 分析用户需求 → 需要检查多台服务器的健康状态
2. 判断为多服务器巡检任务 → 调用 SSH 远程工具
3. 依次检查所有注册的生产服务器
4. 综合所有数据，生成巡检报告
```

### 工具调用

```
工具: ssh_server_health(server_name="prod-web-01")
结果: CPU 45.2% | 内存 62.3% | 磁盘 55% ✅ 正常

工具: ssh_server_health(server_name="prod-web-02")
结果: CPU 52.8% | 内存 68.7% | 磁盘 58% ✅ 正常

工具: ssh_server_health(server_name="prod-db-01")
结果: CPU 72.5% | 内存 82.1% | 磁盘 78.5% ⚠️ 关注

工具: ssh_server_health(server_name="prod-cache-01")
结果: CPU 35.1% | 内存 45.6% | 磁盘 35% ✅ 正常
```

### 最终报告

```json
{
  "title": "CloudShop 生产环境健康巡检报告",
  "timestamp": "2026-08-17 00:00:00",
  "risk_level": "medium",
  "servers_checked": 4,
  "summary": "发现 1 台服务器存在中高风险：prod-db-01",
  "issues": [
    {
      "server": "prod-db-01",
      "problem": "CPU 72.5%（超过 70% 阈值）",
      "impact": "数据库查询延迟可能增加，影响订单系统",
      "suggestion": "1. 检查是否有慢查询 2. 考虑增加读副本 3. 优化连接池"
    },
    {
      "server": "prod-db-01",
      "problem": "内存 82.1%（超过 80% 阈值）",
      "impact": "PostgreSQL 缓冲区紧张，可能导致 OOM",
      "suggestion": "1. 检查 shared_buffers 配置 2. 监控增长趋势 3. 规划扩容"
    }
  ]
}
```

### 展示要点
- ✅ 多服务器并行检查
- ✅ 自动识别风险指标（CPU > 70%，内存 > 80%）
- ✅ 结构化巡检报告
- ✅ 给出可操作的处理建议

---

## Demo 2：Kubernetes 故障诊断

### 目标
展示 AI Agent 对 Kubernetes Pod 异常的自动诊断能力。

### 用户输入

```
为什么订单服务一直重启？帮我排查一下
```

### Agent 思考流程

```
1. 分析用户需求 → 用户反馈 Pod 异常（不断重启）
2. 判断为 Kubernetes 故障场景 → 调用 K8s 工具
3. 获取 Pod 列表 → 识别异常 Pod
4. 调用 describe_pod 获取详细故障信息
5. 调用 logs 获取应用日志辅助分析
6. 综合诊断，生成故障报告
```

### 工具调用

```
工具: kubectl_get_pods(namespace="production")
结果:
  - user-service-7d8b6f8d9c-abcde  Running  1/1
  - order-service-9f4k2d7a1b-klmno  Running  2/2  (restarts: 1)
  - order-service-9f4k2d7a1b-pqrst  Running  2/2
  - payment-service-3b7c1d5e2f-uvwxy  Running  1/1

⚠️ 发现 order-service-9f4k2d7a1b-klmno 有重启记录

工具: kubectl_describe_pod(pod_name="order-service-9f4k2d7a1b-klmno", namespace="production")
结果:
  {
    "name": "order-service-9f4k2d7a1b-klmno",
    "namespace": "production",
    "status": "Running",
    "issues": [
      {
        "type": "OOMKilled",
        "count": 1,
        "last_time": "2026-08-14T14:30:00Z",
        "message": "Container order-api was OOM killed (内存耗尽)"
      }
    ]
  }

工具: kubectl_logs(pod_name="order-service-9f4k2d7a1b-klmno", namespace="production", tail=50)
结果: 日志显示 OutOfMemoryError: Java heap space
```

### 最终报告

```markdown
# Kubernetes 故障诊断报告：order-service

## 故障类型
**OOMKilled（内存溢出）**

## 根因分析
- order-service Pod 因内存不足被 OOM Killer 终止
- Java 堆空间不足（OutOfMemoryError: Java heap space）
- 当前内存限制可能低于实际业务需求

## 影响范围
- 订单创建接口短暂不可用
- 影响的精确时间为 2026-08-14 14:30:00

## 修复建议
1. 即时措施：`kubectl_restart_deployment("order-service", "production")`
2. 短期措施：将内存限制从 512Mi 提升至 1Gi
3. 长期措施：分析内存泄漏，优化 JVM 参数
```

### 展示要点
- ✅ 自动识别 Pod 重启异常
- ✅ 调用 describe_pod 获取详细原因
- ✅ 结合日志分析根因
- ✅ 给出分级修复建议

---

## Demo 3：Docker 服务恢复

### 目标
展示 AI Agent 的 Docker 容器管理和异常恢复能力。

### 用户输入

```
查看 prod-web-01 上的 Docker 容器状态，nginx 是不是挂了？
```

### Agent 思考流程

```
1. 分析用户需求 → 远程服务器 Docker 容器状态检查
2. 选择 SSH 远程工具 → 连接 prod-web-01
3. 获取容器列表 → 检查 nginx 状态
4. 如果异常 → 获取日志辅助分析
5. 生成恢复方案
```

### 工具调用

```
工具: ssh_docker_status(server_name="prod-web-01")
结果:
  - nginx      running  端口: 80:80, 443:443
  - node-app   running  端口: 3000:3000
  - filebeat   running

✅ nginx 运行正常
```

### 最终报告

```markdown
# Docker 容器状态报告：prod-web-01

## 当前状态
| 容器名 | 状态 | 端口映射 | 运行时间 |
|--------|------|----------|----------|
| nginx | ✅ Running | 80:80, 443:443 | 15 天 |
| node-app | ✅ Running | 3000:3000 | 15 天 |
| filebeat | ✅ Running | - | 15 天 |

## 结论
所有容器运行正常，无需干预。
```

### 异常场景变体

如果 nginx 确实挂了：

```markdown
## 异常检测
❌ nginx 容器状态：exited (exit code 1)

## 日志分析（最近 20 行）
[emerg] 1#1: bind() to 0.0.0.0:80 failed (98: Address already in use)

## 恢复方案
1. 检查端口占用：`lsof -i :80`
2. 重启 nginx：`docker restart nginx`
3. 如果持续失败，检查配置文件：`docker exec nginx nginx -t`
```

### 展示要点
- ✅ 远程 Docker 状态查询
- ✅ 容器级健康检查
- ✅ 异常日志获取与分析
- ✅ 恢复方案生成

---

## Demo 4：智能告警分析

### 目标
展示 AI Agent 对 Prometheus 告警的智能分析和根因定位能力。

### 用户输入

```
分析一下最近 prod-db-01 为什么 CPU 偏高
```

### Agent 思考流程

```
1. 分析用户需求 → 数据库服务器 CPU 异常分析
2. 检查历史告警 → 确认近期 CPU 告警记录
3. 调用健康检查获取当前状态
4. 调用系统日志查看异常进程
5. 调用 Docker 状态查看数据库容器
6. 综合分析，生成故障分析报告
```

### 工具调用

```
工具: ssh_server_health(server_name="prod-db-01")
结果: CPU 72.5% | 内存 82.1% | 磁盘 78.5%

工具: ssh_system_logs(server_name="prod-db-01", service="postgres", level="error")
结果: 发现大量慢查询日志 (duration > 5000ms)

工具: ssh_docker_status(server_name="prod-db-01")
结果: postgres running, pgbouncer running
```

### 最终报告

```json
{
  "severity": "high",
  "problem": "prod-db-01 CPU 持续高于 70%（当前 72.5%）",
  "possible_reasons": [
    "数据库慢查询突增（最近 1 小时检测到 15 条 > 5s 的慢查询）",
    "连接池耗尽导致连接排队重试",
    "订单系统峰值流量导致数据库负载上升"
  ],
  "suggestions": [
    "紧急：检查 pg_stat_activity，终止长时间运行的查询",
    "短期：增加 pgbouncer 连接池大小",
    "长期：对慢查询涉及的 SQL 添加索引优化",
    "规划：考虑增加只读副本分担查询负载"
  ],
  "referenced_alerts": [
    "2026-08-14 订单服务响应超时",
    "2026-08-12 prod-db-01 磁盘使用率告警"
  ]
}
```

### 展示要点
- ✅ 结合历史告警数据
- ✅ 主动调用系统日志获取证据
- ✅ 分析根因（慢查询 + 连接池）
- ✅ 分级给出紧急/短期/长期建议
- ✅ 关联相关历史事件

---

## 演示流程建议

### 准备工作

```bash
# 1. 初始化 Demo 数据
python scripts/demo/init_all.py

# 2. 启动后端服务
uvicorn app.main:app --reload

# 3. 启动前端
cd frontend && npm run dev
```

### 演示顺序

| 序号 | 场景 | 时间 | 核心亮点 |
|------|------|------|----------|
| 1 | 服务器巡检 | 3 分钟 | 多服务器 + 自动风险识别 |
| 2 | K8s 故障诊断 | 5 分钟 | Pod 异常排查 + 根因分析 |
| 3 | Docker 恢复 | 3 分钟 | 容器管理 + 恢复方案 |
| 4 | 告警分析 | 4 分钟 | 历史关联 + 分级建议 |

### 面试话术要点

```
1. "我们的 AI Agent 不是简单的聊天机器人，而是能够自主调用工具、
   分析数据、生成专业运维报告的企业级智能体。"

2. "它解决了传统运维中三个核心痛点：人工巡检效率低、
   故障定位依赖经验、监控只能发现问题不能分析原因。"

3. "系统采用 LangGraph 构建 Agent 工作流，支持实时 WebSocket 追踪，
   每个思考步骤和执行结果都对用户透明可见。"
```