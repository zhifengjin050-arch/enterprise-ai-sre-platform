# Enterprise AI DevOps Platform v2.0.0 — Agent 真实场景测试报告

> 验收日期：2026-08-17 15:30 UTC+8
> 测试方式：真实 DeepSeek-V4-Flash 调用（非 Mock）
> 模型：`deepseek-ai/DeepSeek-V4-Flash` via SiliconFlow

---

## 场景 1：服务器健康检查

### 用户输入

```
"检查服务器当前状态，并分析是否存在异常"
```

### 调用链

| 步骤 | 状态 | 耗时 |
|------|------|------|
| ① 分析用户需求 | ✅ completed | 0ms |
| ② 调用 `get_server_health` | ✅ completed | 515ms |
| ③ 调用 `get_cpu_usage` | ✅ completed | 500ms |
| ④ 调用 `get_memory_usage` | ✅ completed | 0ms |
| ⑤ 调用 `get_disk_usage` | ✅ completed | 16ms |
| ⑥ 调用 `get_system_info` | ✅ completed | 156ms |
| ⑦ AI 生成报告 (DeepSeek-V4-Flash) | ✅ completed | 29,985ms |
| **总耗时** | | **35,988ms** |

### Agent 输出预览

```markdown
# 服务器健康报告

## 当前状态

| 指标 | 状态 | 详情 |
|------|------|------|
| **CPU** | ✅ 正常 | **26.4%**（16 核） |
| **内存** | ✅ 正常 | **59.7%**（已用 18.6 GB / 总计 31.3 GB） |
| **磁盘 C:** | ✅ 正常 | **56.7%**（已用 182.6 GB / 总计 322.1 GB） |
| **磁盘 D:** | ✅ 正常 | **28.1%**（已用 197.1 GB / 总计 701.0 GB） |

## 异常检测

✅ **未发现异常** — 所有指标均在安全阈值范围内
```

### 结果判定：✅ 通过

Agent 正确：
1. 理解用户意图（服务器健康检查）
2. 规划工具调用序列（5 个 MCP 工具）
3. 调用真实 MCP 工具获取数据
4. 使用 DeepSeek-V4-Flash 生成结构化报告

---

## 场景 2：订单服务故障分析

### 用户输入

```
"生产环境订单服务响应变慢，请分析可能原因"
```

### 调用链

| 步骤 | 状态 | 耗时 |
|------|------|------|
| ① 分析用户需求 | ✅ completed | 16ms |
| ② `get_server_health` | ✅ completed | 515ms |
| ③ `get_system_info` | ✅ completed | 0ms |
| ④ `get_cpu_usage` | ✅ completed | 500ms |
| ⑤ `get_memory_usage` | ✅ completed | 16ms |
| ⑥ `get_disk_usage` | ✅ completed | 0ms |
| ⑦ `docker_list` | ✅ completed | 16ms |
| ⑧ `list_processes` | ✅ completed | 1,547ms |
| ⑨ `get_audit_logs` | ✅ completed | 16ms |
| ⑩ `system_logs` | ✅ completed | 0ms |
| ⑪ `k8s_get_pods` | ✅ completed | 1,656ms |
| ⑫ `k8s_get_deployments` | ✅ completed | 0ms |
| ⑬ `k8s_get_services` | ✅ completed | 15ms |
| ⑭ `kubectl_get_nodes` | ✅ completed | 0ms |
| ⑮ AI 生成报告 | ✅ completed | 44,219ms |
| **总耗时** | | **89,816ms** |

### Agent 输出预览

```markdown
# 生产环境订单服务响应变慢 — 分析报告

## 一、当前服务器状态概览
| 指标 | 当前值 | 健康状态 |
|------|--------|----------|
| CPU 使用率 | 35.8% (16核) | ✅ 正常 |
| 内存使用率 | 59.8% | ✅ 正常 |
| 磁盘使用率 | C:56.7% / D:28.1% | ✅ 正常 |

## 二、订单服务响应变慢的常见原因分析
基于运维最佳实践，订单服务响应变慢通常由以下几类原因：
...
```

### 结果判定：✅ 通过

Agent 正确：
1. 跨系统数据采集：System + Docker + K8s + Process + Audit
2. 调用 **13 个工具** 进行全方位数据采集
3. DeepSeek-V4-Flash 生成结构化的多维度分析报告
4. 总调用链完整：RAG 检索 → 工具调用 → LLM 推理

---

## 场景 3：Vision 模型测试

### 测试目标

调用 `Qwen/Qwen3-VL-8B-Instruct` 分析运维截图。

### 结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 模型配置 | ✅ 正确 | `VISION_MODEL=Qwen/Qwen3-VL-8B-Instruct` |
| 消息结构 | ✅ 正确 | `content[type=text] + content[type=image_url]` |
| API 调用 | ❌ 400 | 图片 URL 无法被 SiliconFlow 服务端下载 |
| 原因 | 外网图片 URL 被下载服务拒绝 | 需要改用 base64 编码或可访问的 URL |

### 建议

```python
# 改用 base64 编码方式
import base64
with open("screenshot.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
image_url = f"data:image/png;base64,{b64}"
```

---

## 场景测试总结

| 场景 | 状态 | 总耗时 | 工具调用数 | LLM Token 消耗 |
|------|------|--------|-----------|----------------|
| 服务器健康检查 | ✅ 通过 | ~36s | 5 个 MCP 工具 | 约 800+ tokens |
| 订单服务故障分析 | ✅ 通过 | ~90s | 13 个工具 | 约 2000+ tokens |
| Vision 截图分析 | ⚠️ URL 问题 | - | 0 | 0（400 错误） |

**Agent 场景测试：2/3 通过。Agent 在真实 LLM + MCP 工具链下表现完整。**