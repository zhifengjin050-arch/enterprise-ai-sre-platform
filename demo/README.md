# Enterprise AI SRE Platform — Demo 数据包

> **版本**: v3.3.0  
> **用途**: 面试展示 / 功能体验 / 快速上手指南  
> **前置条件**: Docker Compose 启动或本地 uvicorn 运行

---

## 场景概览

| 场景 | 用户输入 | 展示能力 |
|------|----------|----------|
| **K8s 502 故障排查** | "生产环境 payment-service 出现大量 502，请分析原因" | Agent + K8s Tools + RAG + 结构化报告 |

---

## 快速开始

```bash
# 1. 确保项目已启动
# 2. 注册账号并登录（控制台 → 注册）
# 3. 导入 Demo 知识库文档
python demo/import_demo_data.py
# 4. 在 /ops 页面输入故障查询
```

---

## 数据文件说明

| 文件 | 内容 | 用途 |
|------|------|------|
| `incidents/payment_502_incident.json` | 完整 502 故障场景定义 | 演示剧本 |
| `logs/nginx_error.log` | Nginx 反向代理错误日志 | Agent 日志分析 |
| `logs/payment_service.log` | 支付服务应用日志 (Java) | Agent 日志分析 |
| `knowledge/k8s_troubleshooting.md` | K8s 故障排查手册 | RAG 知识检索 |
| `knowledge/nginx_common_issues.md` | Nginx 常见问题指南 | RAG 知识检索 |
| `knowledge/deployment_guide.md` | 生产部署规范 | RAG 知识检索 |
| `import_demo_data.py` | 自动导入脚本 | 一键导入所有知识文档 |

---

## 预期效果

Agent 将自动：
1. 调用 `k8s_pods / k8s_logs` 获取集群状态
2. 调用 `system_logs` 获取系统日志
3. 通过 RAG 检索相关运维文档
4. 生成结构化 Incident Report：

```
## Incident Report

### 问题摘要
生产环境 payment-service 出现大规模 502 Bad Gateway

### 影响范围
- 支付接口不可用
- 影响所有涉及支付的业务线

### 根因分析
- Pod 内存溢出 (OOMKilled) → 容器重启
- Nginx upstream 连接池耗尽

### 诊断证据
[K8s Pod 状态 / 日志片段 / RAG 引用]

### 建议处理方案
1. 调整资源 limits
2. 扩容副本数
3. 配置 HPA 自动伸缩

### 风险等级
🔴 严重

### 后续优化建议
- 增加 PodDisruptionBudget
- 配置 ReadinessProbe
- 实现熔断降级
```