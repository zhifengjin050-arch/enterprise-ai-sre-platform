"""Prometheus 指标定义

定义所有监控指标的 Prometheus Counter / Gauge / Histogram。
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

# ============================================================
# HTTP 请求指标
# ============================================================
http_requests_total = Counter(
    "devops_http_requests_total",
    "HTTP 请求总数",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "devops_http_request_duration_seconds",
    "HTTP 请求耗时（秒）",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ============================================================
# 系统资源指标
# ============================================================
cpu_usage_gauge = Gauge(
    "devops_cpu_usage_percent",
    "CPU 使用率（百分比）",
    ["host"],
)

memory_usage_gauge = Gauge(
    "devops_memory_usage_percent",
    "内存使用率（百分比）",
    ["host"],
)

disk_usage_gauge = Gauge(
    "devops_disk_usage_percent",
    "磁盘使用率（百分比）",
    ["host", "mount"],
)

# ============================================================
# Agent 运行指标
# ============================================================
agent_requests_total = Counter(
    "devops_agent_requests_total",
    "Agent 调用总次数",
)

agent_success_total = Counter(
    "devops_agent_success_total",
    "Agent 执行成功次数",
)

agent_errors_total = Counter(
    "devops_agent_errors_total",
    "Agent 执行错误次数",
)

agent_duration_seconds = Histogram(
    "devops_agent_duration_seconds",
    "Agent 执行耗时（秒）",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0),
)

agent_tools_called_total = Counter(
    "devops_agent_tools_called_total",
    "Agent 工具调用总次数",
    ["tool_name"],
)

# ============================================================
# LLM 指标
# ============================================================
llm_request_duration_seconds = Histogram(
    "devops_llm_request_duration_seconds",
    "LLM 请求耗时（秒）",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0),
)

llm_token_usage_total = Counter(
    "llm_token_usage",
    "LLM Token 消耗总量",
    ["model", "type"],
)

llm_requests_total = Counter(
    "llm_requests_total",
    "LLM 请求总次数",
)

llm_latency_seconds = Histogram(
    "llm_latency",
    "LLM 调用耗时（秒）",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0),
)

# ============================================================
# Agent v3.1 业务指标
# ============================================================
agent_execution_total = Counter(
    "agent_execution_total",
    "Agent 执行总次数",
)

agent_failure_total = Counter(
    "agent_failure_total",
    "Agent 执行失败次数",
)

agent_latency_seconds = Histogram(
    "agent_latency",
    "Agent 执行耗时（秒）",
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0),
)

# ============================================================
# MCP 业务指标
# ============================================================
mcp_tool_call_total = Counter(
    "mcp_tool_call_total",
    "MCP 工具调用次数",
    ["tool"],
)

mcp_tool_error_total = Counter(
    "mcp_tool_error_total",
    "MCP 工具调用失败次数",
    ["tool"],
)

# ============================================================
# Auto Repair 业务指标
# ============================================================
repair_success_total = Counter(
    "repair_success_total",
    "自动修复成功次数",
)

repair_failed_total = Counter(
    "repair_failed_total",
    "自动修复失败次数",
)

# ============================================================
# Kubernetes 指标
# ============================================================
k8s_pods_total = Gauge(
    "devops_k8s_pods_total",
    "Kubernetes Pod 总数",
    ["namespace"],
)

k8s_pods_running = Gauge(
    "devops_k8s_pods_running",
    "Kubernetes Running Pod 数",
    ["namespace"],
)

k8s_pods_pending = Gauge(
    "devops_k8s_pods_pending",
    "Kubernetes Pending Pod 数",
    ["namespace"],
)

k8s_pods_failed = Gauge(
    "devops_k8s_pods_failed",
    "Kubernetes 异常 Pod 数",
    ["namespace"],
)

# ============================================================
# Docker 指标
# ============================================================
docker_containers_total = Gauge(
    "devops_docker_containers_total",
    "Docker 容器总数",
    ["host"],
)

docker_containers_running = Gauge(
    "devops_docker_containers_running",
    "Docker 运行中容器数",
    ["host"],
)

# ============================================================
# 工具函数
# ============================================================

def get_metrics() -> str:
    """获取 Prometheus 格式的指标文本"""
    return generate_latest(REGISTRY).decode("utf-8")


def observe_llm_request(duration: float, tokens: int = 0, model: str = "unknown"):
    """记录 LLM 请求耗时与 Token"""
    llm_request_duration_seconds.observe(duration)
    llm_latency_seconds.observe(duration)
    llm_requests_total.inc()
    if tokens:
        llm_token_usage_total.labels(model=model, type="total").inc(tokens)


def observe_agent_execution(duration: float, success: bool, tools_called: int):
    """记录 Agent 执行"""
    agent_requests_total.inc()
    agent_execution_total.inc()
    agent_duration_seconds.observe(duration)
    agent_latency_seconds.observe(duration)
    if success:
        agent_success_total.inc()
    else:
        agent_errors_total.inc()
        agent_failure_total.inc()


def record_tool_call(tool_name: str):
    """记录工具调用"""
    agent_tools_called_total.labels(tool_name=tool_name).inc()


def record_mcp_tool(tool_name: str, success: bool = True):
    mcp_tool_call_total.labels(tool=tool_name).inc()
    if not success:
        mcp_tool_error_total.labels(tool=tool_name).inc()


def record_repair(success: bool):
    if success:
        repair_success_total.inc()
    else:
        repair_failed_total.inc()


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录 HTTP 请求"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
