# Enterprise AI SRE Platform — Demo 演示指南

> **版本**: v3.3.0  
> **目标**: 让面试官/评估者在 **5 分钟内理解项目核心价值**  
> **前置条件**: Docker 环境或 Python 3.12+

---

## 1. 快速启动 Demo

### 方式 A：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/enterprise-ai-sre-platform.git
cd enterprise-ai-sre-platform

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 SILICONFLOW_API_KEY

# 3. 一键启动
docker compose up -d

# 4. 等待服务就绪（约 30 秒）
docker compose ps

# 5. 打开浏览器访问 http://localhost
```

### 方式 B：本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
alembic upgrade head

# 3. 启动服务
python run.py

# 4. 打开 http://localhost:8000
```

---

## 2. Demo 流程（总时长约 5 分钟）

### Step 1: 注册与登录（30 秒）

1. 打开浏览器访问 http://localhost:8000（Docker 方式为 http://localhost）
2. 点击「注册」按钮
3. 填写用户名、邮箱、密码
4. 注册成功后自动登录，进入 **Executive Dashboard**

> **展示亮点**: JWT 认证、双栏品牌注册页、一键登录

### Step 2: 导入 Demo 知识库（1 分钟）

```bash
# 终端执行导入脚本
python demo/import_demo_data.py
```

脚本会自动：
1. 注册 `demo_admin` 账号
2. 登录获取 JWT Token
3. 上传 3 个运维知识文档到 RAG 知识库：
   - **K8s 故障排查手册** — Pod 诊断、OOMKilled 处理、502 排查
   - **Nginx 常见问题指南** — 502/504 错误、upstream 连接池
   - **生产部署规范** — 资源配置、健康检查、HPA 自动伸缩

> **展示亮点**: RAG 知识库一键导入、语义检索准备就绪

### Step 3: 查看 Knowledge Hub（30 秒）

1. 点击左侧导航栏 **Knowledge**（或访问 `/knowledge`）
2. 可以看到已导入的 3 个文档
3. 点击文档查看详情
4. 尝试在搜索框输入 "OOMKilled" — 语义检索命中相关片段

> **展示亮点**: 企业知识库 UI、RAG 语义检索、多租户准备

### Step 4: 核心 Demo — 502 故障排查（2 分钟）

1. 点击左侧导航栏 **AI Copilot**（或访问 `/ops`）
2. 在输入框中输入：

```
生产环境 payment-service 出现大量 502，请分析原因
```

3. 观察 Agent 自动执行全过程（SSE 流式输出实时展示）：

| 时间 | Agent 操作 | 实时显示 |
|------|-----------|---------|
| 0-3s | 分析意图 → "故障诊断" | Agent 开始推理 |
| 3-6s | `k8s_get_pods(namespace=production)` | Pod CrashLoopBackOff |
| 6-9s | `k8s_logs(payment-service-xxx)` | Java OutOfMemoryError |
| 9-12s | `knowledge_search("502 K8s OOMKilled")` | RAG 命中 → 引用原文 |
| 12-15s | `system_logs()` | Nginx 日志 18 条 502 |
| 15-20s | LLM 综合推理 | 生成完整 Incident Report |

4. 最终输出 **结构化故障分析报告**，包含：
   - 问题摘要
   - 影响范围
   - 根因分析（RCA）
   - 诊断证据（附工具调用结果引用）
   - 建议处理方案
   - 风险等级
   - 后续优化建议

> **展示亮点**: AI Agent 自然语言运维、MCP 工具调用、RAG 知识检索、SSE 实时流式输出、结构化故障报告

### Step 5: Agent Trace 查看（30 秒）

1. 点击左侧导航栏 **Traces**（或访问 `/traces`）
2. 可以看到上一步的 Agent 执行记录
3. 点击记录查看详细 **瀑布时间线**
4. 每一步工具调用的输入、输出、耗时清晰可见

> **展示亮点**: Agent 全链路可观测、工具调用溯源、面试可追问 Trace 实现

### Step 6: 其他功能浏览（1 分钟）

| 页面 | 路由 | 展示内容 |
|------|------|---------|
| **Executive Dashboard** | `/overview` | 系统健康评分、Agent 执行趋势 |
| **Infrastructure** | `/infra` | 服务器列表、Docker 容器、K8s Pod 状态 |
| **Incidents** | `/incidents` | 告警列表、Auto Repair 审批 |
| **Monitor** | `/monitor` | 实时指标 + Grafana iframe |

---

## 3. Demo 剧本（面试场景）

### 场景：面试官提问 "这个系统能做什么？"

**你的回答框架：**

> "这是一个基于 LangGraph 构建的 AI SRE Agent 平台，核心能力是让运维人员通过自然语言完成故障排查。我给您演示一个真实场景："
>
> （打开浏览器，执行 Step 4）
>
> "您看，我输入 '生产环境 payment-service 出现 502'，Agent 自动做了几件事：
> 1. 调用 K8s 工具检查 Pod 状态 — 发现 CrashLoopBackOff
> 2. 查看 Pod 日志 — 发现 OOMKilled
> 3. 从知识库检索相关故障手册 — 命中 OOMKilled 处理流程
> 4. 查看 Nginx 日志 — 发现 18 条连接失败
> 5. 最后 LLM 综合分析，生成完整的故障报告"
>
> "整个过程从原来的 30 分钟人工排查缩短到 20 秒。而且每一步都有 Trace 记录，可以追溯到每一个工具调用。"

### 场景：面试官提问 "RAG 知识库怎么工作的？"

**你的回答框架：**

> "知识库支持两种方式：一种是手动上传文档，另一种是通过飞书连接器自动同步。文档上传后会自动切分、向量化、存储到 pgvector。当 Agent 运行时，会根据问题语义检索最相关的知识片段，注入到 LLM 上下文中。"
>
> （打开 `/knowledge` 页面展示）
>
> "您看这里已经导入了 3 个运维文档。每个文档都做了语义切分，搜索 'OOMKilled' 能直接命中相关章节。而且 v3.3 实现了多租户隔离，不同组织的数据完全隔离。"

### 场景：面试官提问 "MCP 协议是什么？"

> "MCP 是 Model Context Protocol，它定义了一套标准化的工具发现和调用协议。我们的平台作为 MCP Client，可以动态连接任何实现了 MCP Server 的工具服务。这样工具扩展就不需要改 Agent 代码了，新工具只需实现 MCP 协议就能被 Agent 自动发现和使用。"

---

## 4. 故障排查自检

如果在 Demo 过程中遇到问题，请参考以下排查步骤：

| 问题 | 原因 | 解决 |
|------|------|------|
| 注册/登录失败 | 数据库未初始化 | `alembic upgrade head` |
| 导入脚本报 401 | 后端未启动 | 检查 `python run.py` |
| 知识库搜索无结果 | Demo 数据未导入 | `python demo/import_demo_data.py` |
| Agent 工具调用失败 | MCP Server 未配置 | 检查 .env 中 MCP_SERVER_CWD |
| SSE 无响应 | LLM API Key 无效 | 检查 SILICONFLOW_API_KEY |
| 前端页面 404 | Docker 未构建前端 | `docker compose build` |

---

## 5. Demo 成功标准

| 检查项 | 标准 |
|--------|------|
| 注册/登录 | 成功注册并获取 JWT Token |
| Demo 数据导入 | 3 个知识文档成功上传 |
| Knowledge Hub | 文档列表可见，语义搜索可命中 |
| Agent 故障诊断 | Agent 自动调用 K8s 工具 + 知识检索 |
| 故障报告输出 | 输出结构化 Incident Report |
| Agent Trace | Trace 记录完整，工具调用可追溯 |

---

> **文档版本**: v3.3.0 | **更新日期**: 2026-08-18 | **返回**: [README](../README.md)