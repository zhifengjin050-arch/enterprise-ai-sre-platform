# RAG 知识库 + Agent 长期记忆演示场景

> 本文档演示 AI DevOps Agent 的企业知识库（RAG）和长期记忆能力。
> 展示 Agent 如何利用企业积累的运维知识进行智能故障排查。

---

## Demo 1：知识库辅助故障排查

### 场景

用户遇到 Kubernetes Pod 崩溃问题，Agent 利用知识库中的运维文档进行排查。

### 用户输入

```
订单服务 Pod 一直在 CrashLoopBackOff，帮我看看原因
```

### Agent 思考流程

```
1. 分析用户需求 → Kubernetes Pod 故障排查
2. 系统自动检索知识库 → 找到 "K8s 排障指南" 相关文档
3. 系统加载长期记忆 → 发现之前有类似 OOM 故障记录
4. 参考知识库 SOP：
   - 先用 kubectl describe pod 查看事件
   - 再用 kubectl logs 查看日志
5. 调用 kubectl_describe_pod 获取 Pod 状态
6. 调用 kubectl_logs 获取应用日志
7. 综合分析 → 输出故障报告
```

### 知识库检索结果

```json
{
  "query": "Pod CrashLoopBackOff 排查",
  "matched_docs": [
    {
      "title": "Kubernetes 排障指南",
      "relevance": 0.92,
      "content": "当 Pod 处于 CrashLoopBackOff 状态时，首先检查日志。常见的原因为 OOMKilled、配置错误、镜像不存在。"
    },
    {
      "title": "订单服务架构文档",
      "relevance": 0.78,
      "content": "订单服务依赖数据库连接池，默认配置 max_connections=20。当并发过高时可能出现连接池耗尽。"
    }
  ]
}
```

### 最终报告

```json
{
  "title": "订单服务 CrashLoopBackOff 诊断报告",
  "risk_level": "high",
  "root_cause": "数据库连接池耗尽 - max_connections=20 不足以支撑峰值流量",
  "evidence": [
    "Pod 状态: CrashLoopBackOff (重启 12 次)",
    "OOM 事件: 无",
    "日志错误: 'could not acquire connection from pool - timeout'"
  ],
  "solution": "1. 增加数据库连接池配置 max_connections=50\n2. 添加连接池监控指标\n3. 考虑增加 Pod 副本数",
  "knowledge_source": "K8s 排障指南 + 订单服务架构文档"
}
```

---

## Demo 2：长期记忆辅助历史问题追溯

### 场景

用户询问之前类似问题的解决方案。

### 用户输入

```
之前支付服务好像也出过类似问题，当时怎么解决的？
```

### Agent 处理流程

```
1. 分析用户需求 → 追溯历史故障
2. 系统检索长期记忆 → 找到 3 天前的支付服务故障记录
3. 历史记录显示：
   - 支付服务 OOM (2026-08-14)
   - 解决方案: 增加 memory limit 从 256Mi 到 512Mi
   - 调用 kubectl describe pod 确认
4. 输出历史解决方案参考
```

### 历史记忆检索

```json
{
  "query": "支付服务故障",
  "historical_records": [
    {
      "date": "2026-08-14 14:23:00",
      "category": "解决方案",
      "summary": "支付服务 OOM 崩溃，通过增加 memory limit 解决",
      "detail": "支付服务 Pod 持续 OOMKilled, 将 resources.limits.memory 从 256Mi 提升至 512Mi 后恢复正常"
    }
  ]
}
```

### Agent 回答

```
关于支付服务之前的类似问题：

📅 2026-08-14 支付服务 OOM 故障：
- 现象：Pod 持续 OOMKilled，与当前订单服务的表现类似
- 原因：memory limit 设置过低 (256Mi)
- 解决方案：将 memory limit 提升至 512Mi 后恢复

建议检查当前订单服务的资源限制配置是否也存在类似问题。
```

---

## Demo 3：企业知识库构建与维护

### 适合导入的知识类型

| 类型 | 示例 | 价值 |
|------|------|------|
| 运维手册 | Linux 基础运维、网络排查 | 标准化运维流程 |
| K8s 规范 | Deployment 配置规范、命名空间规划 | 集群管理标准化 |
| 故障处理 SOP | 数据库连接池耗尽处理、OOM 排查 | 快速故障恢复 |
| 架构文档 | 微服务依赖关系、数据流图 | 系统全局理解 |
| 应急预案 | 容灾切换流程、数据恢复步骤 | 高可用保障 |

### 导入方式

```bash
# API 导入
curl -X POST http://localhost:8000/api/knowledge/upload \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Kubernetes 排障指南",
    "content": "# Pod 故障排查流程\n\n1. 使用 kubectl describe pod 查看事件\n2. 使用 kubectl logs 查看日志\n..."
  }'

# Web 界面导入
# 访问 → http://localhost/knowledge → 上传文档
```

---

## 企业价值

| 能力 | 传统方式 | AI Agent + RAG |
|------|---------|---------------|
| 知识传承 | 依赖资深工程师口口相传 | 企业知识数字化、可检索 |
| 故障排查 | 翻阅文档、搜索历史记录 | 自动检索相关知识辅助分析 |
| 新人培训 | 长时间跟班学习 | 知识库即学即用 |
| 标准化 | 难以保证所有人遵循 SOP | Agent 自动按 SOP 执行排查 |
| 持续积累 | 故障解决后缺乏记录 | 每次故障自动进入长期记忆 |