# 企业应用场景手册 — Enterprise AI DevOps Platform

> **文档版本**: v1.0  \n> **适用版本**: v1.3.0  \n> **场景类型**: 真实企业运维案例

---

## 场景一：生产服务器自动巡检

### 问题背景

某电商平台运维团队每天需要手动检查 20+ 台生产服务器的健康状态，包括 CPU 使用率、内存占用、磁盘空间和关键进程运行情况。每台服务器检查约 5 分钟，整个巡检耗时 2 小时以上。且人工巡检容易遗漏异常，曾导致多次线上故障未能提前发现。

### 传统方式

```bash
# 运维人员需逐台 SSH 登录执行命令
ssh prod-web-01 "top -bn1 | head -5"
ssh prod-web-01 "df -h"
ssh prod-db-01 "top -bn1 | head -5"
ssh prod-db-01 "df -h"
# ... 重复 20+ 次
# 然后人工汇总到 Excel 表格
```

痛点：
- 耗时 2+ 小时 / 天
- 容易遗漏服务器
- 异常发现滞后
- 巡检结果无统一存档

### AI 方案

运维人员在 AI DevOps Platform 中输入一句话指令，Agent 自动完成全量巡检。

```
用户：巡检所有生产服务器
```

### 技术流程

```
1. 用户输入 → POST /api/chat
2. Agent 分析请求 → 识别为"批量服务器巡检"
3. 加载短期记忆 → 获取当前上下文
4. 加载长期记忆 → 检索上次巡检发现的异常
5. 检索 RAG 知识库 → 获取《生产服务器巡检 SOP》
6. System Prompt 注入: "按照以下 SOP 巡检所有生产服务器..."
7. Agent 调用 server_health (本地) → 本机指标
8. Agent 调用 ssh_server_health → 登录 prod-web-01
9. Agent 调用 ssh_server_health → 登录 prod-web-02
10. Agent 调用 ssh_server_health → 登录 prod-db-01
11. ... 逐个执行所有服务器
12. LLM 综合分析所有结果
13. 生成巡检报告（Markdown 格式）
```

**示例输出**：

```
# 生产服务器巡检报告

巡检时间：2026-08-17 10:00:00
巡检服务器：5 台

## 异常摘要

| 服务器 | 异常 | 严重程度 |
|--------|------|---------|
| prod-db-01 | 磁盘使用率 92% | 🔴 严重 |
| prod-web-02 | 内存使用率 87% | 🟡 警告 |

## 详细结果

### prod-web-01 ✅
- CPU: 32% | 内存: 55% | 磁盘: 62%
- Docker 容器: 全部正常运行

### prod-db-01 🔴
- CPU: 45% | 内存: 72% | **磁盘: 92%**
- 建议: 清理历史归档日志，或扩容磁盘

### prod-web-02 🟡
- CPU: 28% | **内存: 87%** | 磁盘: 45%
- 建议: 检查是否存在内存泄漏，考虑重启服务

## 操作建议
1. [紧急] prod-db-01 磁盘清理：`docker system prune`
2. [关注] prod-web-02 内存：安排排查计划
```

### 收益

| 指标 | 传统方式 | AI 方式 | 提升 |
|------|---------|---------|:----:|
| 巡检耗时 | 2 小时 | 3 分钟 | **40x** |
| 服务器覆盖 | 易遗漏 | 100% 覆盖 | — |
| 异常发现 | 依赖经验 | AI 自动标记 | — |
| 报告生成 | 手动 Excel | 自动 Markdown | — |
| 历史追溯 | 散落各处 | 数据库持久化 | — |

---

## 场景二：Kubernetes 故障诊断

### 问题背景

某微服务架构企业的生产 K8s 集群频繁出现 Pod 异常 —— CrashLoopBackOff、ImagePullBackOff、OOMKilled 等。运维人员需要在多个终端窗口之间切换，执行 `kubectl get pods`、`kubectl describe pod`、`kubectl logs` 等命令组合排查，每次故障平均定位耗时 20 分钟。

### 传统方式

```bash
# Step 1: 查看异常 Pod
kubectl get pods -n production | grep -E "CrashLoop|Error|OOM"

# Step 2: 查看 Pod 详情
kubectl describe pod payment-service-7d8b6f8d9c-abcde -n production

# Step 3: 查看日志
kubectl logs payment-service-7d8b6f8d9c-abcde -n production --tail=50

# Step 4: 查看节点状态
kubectl top nodes

# Step 5: 凭经验判断根因
```

痛点：
- 多命令组合，操作繁琐
- 需要记忆大量 kubectl 命令
- 故障根因判断依赖个人经验
- 新运维工程师上手周期长

### AI 方案

```
用户：帮我诊断 production 命名空间的异常 Pod
```

### 技术流程

```
1. 用户输入 → POST /api/chat
2. Agent 分析 → 识别为 K8s 故障诊断请求
3. 加载长期记忆 → 检索历史 K8s 故障和解决方案
4. 检索 RAG 知识库 → 获取《K8s 故障排查手册》
5. Agent 调用 kubectl_get_pods(namespace="production")
   → 发现 2 个异常 Pod
6. Agent 调用 kubectl_describe_pod(pod="payment-service-xxx", namespace="production")
   → 发现 OOMKilled 状态
7. Agent 调用 kubectl_logs(pod="payment-service-xxx", namespace="production")
   → 发现 OutOfMemoryError
8. Agent 调用 kubectl_get_nodes()
   → 确认节点资源充足，排除节点问题
9. LLM 综合分析 → 根因：内存限制不足
10. 生成诊断报告 + 修复建议
```

**示例输出**：

```
# Kubernetes 故障诊断报告

集群状态检查时间：2026-08-17 14:30:00

## 异常 Pod 摘要

| Pod | 状态 | 命名空间 | 原因 |
|-----|------|---------|------|
| payment-service-abcde | CrashLoopBackOff | production | OOMKilled |
| user-service-fghij | Error | production | ImagePullBackOff |

## 根因分析

### payment-service-abcde — OOMKilled 🔴
- **根因**: 容器内存 limit (512Mi) 不足
- **证据**: Pod 多次因 OOM 被 Kill，日志最后记录为 OutOfMemoryError
- **修复**: 将内存 limit 提升至 1Gi

### user-service-fghij — ImagePullBackOff 🟡
- **根因**: 镜像标签不存在
- **证据**: describe 显示 ImagePullBackOff，镜像 user-service:v2.0.1 未推送到仓库
- **修复**: 推送正确的镜像标签或更正 deployment 中的镜像版本

## 操作建议
1. [立即] 修复 payment-service 内存限制：`kubectl patch deployment payment-service -n production -p '{"spec":{"template":{"spec":{"containers":[{"name":"payment","resources":{"limits":{"memory":"1Gi"}}}]}}}}'`
2. [立即] 推送 user-service:v2.0.1 镜像到仓库
3. [预防] 检查所有服务的资源限制配置
4. [预防] 在 CI 流程增加镜像标签验证步骤
```

### 收益

| 指标 | 传统方式 | AI 方式 | 提升 |
|------|---------|---------|:----:|
| 故障定位时间 | 20 分钟 | 2 分钟 | **10x** |
| 命令学习成本 | 高 | 零 (自然语言) | — |
| 诊断准确率 | 依赖经验 | AI + RAG 知识 | — |
| 新人上手周期 | 2-4 周 | 立即可用 | — |
| 修复方案生成 | 手动 | 自动生成命令 | — |

---

## 场景三：智能告警分析

### 问题背景

某企业的 Prometheus 监控系统每天产生数百条告警。运维团队被大量告警淹没，难以区分严重程度和优先级。同时，相同类型的告警反复出现却没有进行根因追溯，导致团队陷入"告警疲劳"。

### 传统方式

```
告警通知 (飞书群)：
[Warning] CPU 使用率 > 80% - prod-web-01 (15:23:45)
[Warning] CPU 使用率 > 80% - prod-db-01 (15:24:12)
[Critical] 磁盘使用率 > 90% - prod-db-01 (15:25:01)
[Warning] 内存使用率 > 85% - prod-web-02 (15:25:30)
[Warning] CPU 使用率 > 80% - prod-web-01 (15:26:10)
... 每分钟都在刷屏 ...
```

痛点：
- 告警风暴，无法区分优先级
- 同类告警重复出现，无人根因分析
- 告警与故障上下文割裂
- 缺乏智能化分析和建议

### AI 方案

Agent 自动分析告警，去重聚合，并生成根因分析和修复建议。

```
用户：分析最近的告警
```

### 技术流程

```
1. 用户输入请求
2. Agent 调用 alerts API → 获取当前活跃告警列表
3. Agent 调用 server_health → 获取各服务器当前状态
4. Agent 检索长期记忆 → 匹配历史类似告警的解决方案
5. 告警聚合分析：
   - 去重：同一主机连续 CPU 告警合并
   - 关联：磁盘告警 + CPU 告警 → 可能关联
   - 分级：Critical / Warning / Info
6. LLM 生成分析报告
7. 如果发现 Critical 告警，Agent 可主动建议修复操作
```

**示例输出**：

```
# AI 告警分析报告

分析时间：2026-08-17 16:00:00
当前活跃告警：12 条（去重聚合后：4 组）

## 告警聚合结果

### 🚨 [严重] prod-db-01 磁盘使用率 92%
- **持续时间**: 2 小时 15 分钟
- **关联告警**: 无
- **历史记录**: 本月第 3 次出现
- **上次解决方案**: 清理 Docker 日志和归档文件
- **自动修复尝试**: Docker 日志清理脚本已执行，释放 8GB
- **建议**: 扩容 /data 分区至 200GB，或配置日志自动轮转

### ⚠️ [警告] prod-web-01 CPU 波动 (75-85%)
- **持续时间**: 45 分钟
- **关联告警**: 对应时段流量增长 200%
- **分析**: 促销活动流量高峰导致，非异常
- **建议**: 促销期间临时扩容 Pod 副本数

### ⚠️ [警告] prod-web-02 内存 87%
- **持续时间**: 1 小时
- **关联告警**: 无
- **分析**: Node.js 服务疑似内存泄漏
- **建议**: 安排版本回滚并排查内存泄漏

## 处理建议（按优先级）
1. 🔴 prod-db-01 磁盘 —— 扩容或清理
2. 🟡 prod-web-02 内存 —— 排查泄漏
3. 🟢 prod-web-01 CPU —— 促销期间关注即可
```

### 收益

| 指标 | 传统方式 | AI 方式 | 提升 |
|------|---------|---------|:----:|
| 告警处理速度 | 手动筛选 | 自动聚合分析 | **10x** |
| 告警噪音 | 全部推送 | AI 去重分级 | — |
| 根因分析 | 人工排查 | AI 自动关联 | — |
| 修复建议 | 无 | 自动生成 + 历史参考 | — |
| 告警历史追溯 | 散落群消息 | 数据库持久化 | — |

---

## 场景四：企业运维知识助手

### 问题背景

某企业运维团队拥有多年积累的运维经验 —— 故障处理手册、服务器配置规范、安全基线文档等。但这些知识散落在 Wiki、文档、个人笔记中，运维人员遇到问题时需要手动搜索，效率低下。新员工入职后需要花费数周学习这些知识。

### 传统方式

```
运维人员遇到问题：
1. 打开企业 Wiki → 搜索关键词 → 翻阅多篇文档
2. 翻看聊天记录 → 找之前类似问题的讨论
3. 问资深同事 → 打断他人工作
4. 凭经验猜测 → 可能导致误操作

平均耗时：15-30 分钟
```

### AI 方案

将企业运维文档导入 AI DevOps Platform 的知识库，Agent 在回答问题时会自动检索相关知识。

**知识库导入**：

```bash
# 运维人员将 SOP 文档上传到知识库
# 支持格式：.md, .txt
# 支持来源：手动输入、文件上传
```

**对话示例**：

```
用户：生产环境如何安全重启 PostgreSQL 主库？

Agent 检索知识库 → 找到《PostgreSQL 主库重启 SOP》
Agent 结合知识回答：

# PostgreSQL 主库安全重启流程

根据知识库文档《PostgreSQL 主库重启 SOP》，操作步骤如下：

## 前置检查
1. 确认从库同步状态: `pg_isready -h 从库IP`
2. 检查延迟: `SELECT pg_wal_lsn_diff(pg_stat_replication.sent_lsn, pg_stat_replication.replay_lsn) FROM pg_stat_replication;`
3. 确保延迟 < 100MB

## 切换流程
1. 将主库降级: `pg_ctl promote`
2. 将从库升级为主库: `pg_ctl promote`
3. 更新应用连接串指向新主库
4. 验证：`SELECT pg_is_in_recovery();` → 返回 false

## 回滚方案
- 如新主库异常，30 秒内切回原主库
- 命令: `pg_ctl promote`（在原主库执行）

## 注意事项
- 不要直接 `kill -9` PostgreSQL 进程
- 切换前务必确认连接已 drained
- 建议窗口期操作，预留 30 分钟缓冲
```

**更多示例**：

```
用户：Nginx 502 错误怎么排查？

Agent 检索 → 《Nginx 故障排查指南》

回答：
Nginx 502 表示上游服务不可用。请按以下步骤排查：

1. 检查上游服务: `curl http://localhost:8080/health`
2. 检查 Nginx 日志: `tail -100 /var/log/nginx/error.log`
3. 检查后端服务日志: `journalctl -u myapp -n 50`
4. 确认端口监听: `ss -tlnp | grep 8080`

常见原因：
- 后端服务崩溃 → 重启服务
- 后端服务超时 → 增加 proxy_read_timeout
- Unix Socket 文件权限 → 检查 socket 文件权限
```

### 收益

| 指标 | 传统方式 | AI 方式 | 提升 |
|------|---------|---------|:----:|
| 知识查找时间 | 15-30 分钟 | 10 秒 | **90x** |
| 知识覆盖面 | 个人经验 | 团队知识库 | — |
| 新员工上手 | 2-4 周 | 1 周 | **4x** |
| 知识传承 | 依赖个人 | 数字化沉淀 | — |
| 操作准确率 | 经验决定 | SOP 保障 | — |
| 知识更新 | 被动 | 主动上传 | — |

---

## 场景收益总览

| 场景 | 效率提升 | 核心价值 |
|------|:---------:|---------|
| 生产服务器自动巡检 | **40x** | 从 2 小时 → 3 分钟 |
| Kubernetes 故障诊断 | **10x** | 从 20 分钟 → 2 分钟 |
| 智能告警分析 | **10x** | 从告警疲劳 → 智能分级 |
| 企业运维知识助手 | **90x** | 从 30 分钟 → 10 秒 |

---

> **总结**: Enterprise AI DevOps Platform 通过 AI Agent + RAG 知识库 + 自动化工具链，将企业运维效率提升 10-90 倍，同时实现运维知识的数字化沉淀和传承。