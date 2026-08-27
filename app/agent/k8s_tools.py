"""Kubernetes AI 运维工具模块

使用 kubectl --output=json 获取结构化 Kubernetes 集群信息。
所有工具返回统一的 JSON 格式，便于 Agent 分析诊断。

安全设计:
  - 只读操作 (get_pods / get_nodes / logs / describe_pod) 默认允许
  - 修改操作 (restart_deployment) 需要 KUBERNETES_ALLOW_RESTART=true
  - 禁止操作硬编码黑名单：delete / exec / 修改 RBAC / 删除 namespace
"""

import json
import logging
import subprocess
from langchain.tools import tool

from app.config import settings

logger = logging.getLogger("agent")

# Kubernetes 配置（从全局设置读取）
K8S_ENABLED = settings.kubernetes_enabled
K8S_KUBECONFIG = settings.kubeconfig_path or None
K8S_TIMEOUT = settings.kubernetes_timeout
K8S_ALLOW_RESTART = settings.kubernetes_allow_restart

# ============================================================
# kubeconfig 环境变量
# ============================================================
_env: dict[str, str] = {}
if K8S_KUBECONFIG:
    _env["KUBECONFIG"] = K8S_KUBECONFIG


def _build_cmd(args: list[str]) -> list[str]:
    """构建 kubectl 命令，自动注入 kubeconfig"""
    cmd = ["kubectl"]
    if K8S_KUBECONFIG:
        cmd.extend(["--kubeconfig", K8S_KUBECONFIG])
    cmd.extend(args)
    return cmd


def _run_kubectl(args: list[str], timeout: int | None = None) -> dict:
    """执行 kubectl 命令并返回结构化结果

    Args:
        args: kubectl 参数列表
        timeout: 超时秒数，默认使用配置值

    Returns:
        {"success": bool, "data": Any | None, "error": str | None}
    """
    if not K8S_ENABLED:
        return {
            "success": False,
            "error": "Kubernetes 功能未启用（KUBERNETES_ENABLED=false）",
        }

    cmd = _build_cmd(args)
    t = timeout or K8S_TIMEOUT

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=t,
            env=_env or None,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            logger.warning("kubectl 执行失败 (exit=%d): %s", result.returncode, error_msg[:200])
            return {"success": False, "error": error_msg}

        stdout = result.stdout.strip()
        if not stdout:
            return {"success": True, "data": None}

        # 尝试 JSON 解析
        try:
            parsed = json.loads(stdout)
            return {"success": True, "data": parsed}
        except json.JSONDecodeError:
            # 非 JSON 输出（如纯文本），以纯文本方式返回
            return {"success": True, "data": stdout}

    except FileNotFoundError:
        return {"success": False, "error": "未找到 kubectl 命令，请确认已安装 Kubernetes 命令行工具。"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"kubectl 命令执行超时（{t} 秒）。"}
    except Exception as e:
        logger.error("kubectl 执行异常: %s", e)
        return {"success": False, "error": f"kubectl 执行异常: {str(e)}"}


# ============================================================
# 禁止操作黑名单（安全控制）
# ============================================================
_DANGEROUS_OPERATIONS = [
    "delete", "drain", "cord on", "taint", "exec",
    "create clusterrole", "create clusterrolebinding",
    "delete namespace", "delete ns",
]


def _is_safe_command(args: list[str]) -> bool:
    """检查 kubectl 命令是否安全"""
    cmd_str = " ".join(args).lower()
    for op in _DANGEROUS_OPERATIONS:
        if op in cmd_str:
            return False
    return True


# ============================================================
# 工具函数
# ============================================================
def _parse_pod_item(item: dict) -> dict:
    """从 kubectl JSON item 提取 Pod 摘要"""
    metadata = item.get("metadata", {})
    status_obj = item.get("status", {})
    container_statuses = status_obj.get("containerStatuses", [])

    ready_containers = sum(1 for cs in container_statuses if cs.get("ready"))
    total_containers = len(container_statuses)
    restarts = sum(cs.get("restartCount", 0) for cs in container_statuses)

    return {
        "namespace": metadata.get("namespace", ""),
        "name": metadata.get("name", ""),
        "status": status_obj.get("phase", ""),
        "ready": f"{ready_containers}/{total_containers}" if total_containers > 0 else "0/0",
        "node": status_obj.get("hostIP", ""),
        "pod_ip": status_obj.get("podIP", ""),
        "restarts": restarts,
        "age": metadata.get("creationTimestamp", ""),
    }


def _parse_node_item(item: dict) -> dict:
    """从 kubectl JSON item 提取 Node 摘要"""
    metadata = item.get("metadata", {})
    status_obj = item.get("status", {})
    conditions = status_obj.get("conditions", [])
    capacity = status_obj.get("capacity", {})

    # Ready 状态
    ready_status = "Unknown"
    for c in conditions:
        if c.get("type") == "Ready":
            ready_status = "Ready" if c.get("status") == "True" else "NotReady"
            break

    # 节点角色
    labels = metadata.get("labels", {})
    role = "<none>"
    for k in labels:
        if "node-role.kubernetes.io/" in k:
            role = k.split("/")[-1]
            break

    # 内部 IP
    internal_ip = ""
    for addr in status_obj.get("addresses", []):
        if addr.get("type") == "InternalIP":
            internal_ip = addr.get("address", "")
            break

    node_info = status_obj.get("nodeInfo", {})

    return {
        "name": metadata.get("name", ""),
        "status": ready_status,
        "role": role,
        "internal_ip": internal_ip,
        "os_image": node_info.get("osImage", ""),
        "kubelet_version": node_info.get("kubeletVersion", ""),
        "cpu": capacity.get("cpu", "0"),
        "memory": capacity.get("memory", "0"),
        "pods_max": capacity.get("pods", "0"),
    }


# ============================================================
# Tool 1: kubectl_get_pods — 查询 Pod 状态
# ============================================================
@tool
def kubectl_get_pods(namespace: str = "") -> dict:
    """获取 Kubernetes Pod 列表（结构化 JSON）

    查询集群中 Pod 的运行状态，支持按命名空间过滤。

    Args:
        namespace: Kubernetes 命名空间，为空时查询所有命名空间（-A）
    """
    args = ["get", "pods", "--output=json"]
    if namespace:
        args.extend(["-n", namespace])
    else:
        args.append("-A")

    result = _run_kubectl(args)
    if not result.get("success"):
        return result

    raw_items = []
    data = result.get("data")
    if isinstance(data, dict):
        raw_items = data.get("items", [])
    elif isinstance(data, list):
        raw_items = data

    pods = [_parse_pod_item(item) for item in raw_items]
    return {"success": True, "pods": pods, "total": len(pods)}


# ============================================================
# Tool 2: kubectl_get_nodes — 查询集群节点
# ============================================================
@tool
def kubectl_get_nodes() -> dict:
    """获取 Kubernetes 集群节点列表（结构化 JSON）

    查询集群中所有 Node 的状态、角色、资源容量等关键信息。
    """
    result = _run_kubectl(["get", "nodes", "--output=json"])
    if not result.get("success"):
        return result

    raw_items = []
    data = result.get("data")
    if isinstance(data, dict):
        raw_items = data.get("items", [])
    elif isinstance(data, list):
        raw_items = data

    nodes = [_parse_node_item(item) for item in raw_items]
    return {"success": True, "nodes": nodes, "total": len(nodes)}


# ============================================================
# Tool 3: kubectl_logs — 查询 Pod 日志
# ============================================================
@tool
def kubectl_logs(pod_name: str, namespace: str = "default", tail: int = 100) -> dict:
    """获取 Kubernetes Pod 日志

    查询指定 Pod 的最近日志输出，用于排查应用异常。

    Args:
        pod_name: Pod 名称
        namespace: Pod 所在命名空间，默认 default
        tail: 返回最近多少行日志，默认 100
    """
    args = ["logs", pod_name, "-n", namespace, f"--tail={tail}"]
    result = _run_kubectl(args)

    if not result.get("success"):
        return result

    log_content = result.get("data", "")
    if log_content is None:
        log_content = ""
    if isinstance(log_content, dict):
        log_content = json.dumps(log_content, ensure_ascii=False, indent=2)
    else:
        log_content = str(log_content)

    return {
        "success": True,
        "pod_name": pod_name,
        "namespace": namespace,
        "logs": log_content,
        "line_count": len(log_content.splitlines()),
    }


# ============================================================
# Tool 4: kubectl_describe_pod — Pod 故障分析
# ============================================================
@tool
def kubectl_describe_pod(pod_name: str, namespace: str = "default") -> dict:
    """分析 Kubernetes Pod 异常

    获取 Pod 的详细状态，解析容器状态以诊断常见异常：
      - OOMKilled（内存溢出）
      - CrashLoopBackOff（崩溃回退）
      - ImagePullBackOff（镜像拉取失败）
      - Pending（调度失败）

    Args:
        pod_name: Pod 名称
        namespace: Pod 所在命名空间，默认 default
    """
    result = _run_kubectl(["get", "pod", pod_name, "-n", namespace, "--output=json"])
    if not result.get("success"):
        return result

    pod_data = result.get("data")
    if not pod_data:
        return {
            "success": False,
            "error": f"Pod '{pod_name}' 在命名空间 '{namespace}' 中未找到。",
        }

    status_obj = pod_data.get("status", {})

    # 解析容器状态
    container_statuses = status_obj.get("containerStatuses", [])
    containers = []
    issues = []

    for cs in container_statuses:
        state = cs.get("state", {})
        reason = "running"
        exit_code = -1

        if "waiting" in state:
            reason = state["waiting"].get("reason", "Waiting")
        elif "terminated" in state:
            reason = state["terminated"].get("reason", "Terminated")
            exit_code = state["terminated"].get("exitCode", -1)

        container_info = {
            "name": cs.get("name", ""),
            "state": reason,
            "ready": cs.get("ready", False),
            "restart_count": cs.get("restartCount", 0),
            "image": cs.get("image", ""),
            "exit_code": exit_code,
        }
        containers.append(container_info)

        # 自动诊断常见异常
        if reason == "OOMKilled":
            issues.append({
                "severity": "critical",
                "type": "OOMKilled",
                "container": cs.get("name", ""),
                "message": "容器因内存溢出（OOM）被杀死。建议：增加内存 limit 或优化内存使用。",
            })
        elif reason == "CrashLoopBackOff":
            issues.append({
                "severity": "critical",
                "type": "CrashLoopBackOff",
                "container": cs.get("name", ""),
                "message": "容器反复崩溃重启。建议：检查应用代码错误或配置问题。",
            })
        elif reason in ("ImagePullBackOff", "ErrImagePull"):
            issues.append({
                "severity": "high",
                "type": "ImagePullError",
                "container": cs.get("name", ""),
                "message": "镜像拉取失败。建议：检查镜像名称、标签及仓库认证。",
            })
        elif not cs.get("ready") and reason == "Running":
            issues.append({
                "severity": "warning",
                "type": "ReadinessProbeFailed",
                "container": cs.get("name", ""),
                "message": "容器已运行但未通过就绪检查。建议：检查 readiness probe 配置。",
            })

    # Pod 调度分析
    phase = status_obj.get("phase", "")
    if phase == "Pending":
        for condition in status_obj.get("conditions", []):
            if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                issues.append({
                    "severity": "high",
                    "type": "Unschedulable",
                    "container": "",
                    "message": condition.get("message", "Pod 无法调度。建议：检查节点资源是否充足。"),
                })

    return {
        "success": True,
        "pod_name": pod_name,
        "namespace": namespace,
        "phase": phase,
        "containers": containers,
        "issues": issues,
        "has_issues": len(issues) > 0,
    }


# ============================================================
# Tool 5: kubectl_restart_deployment — 滚动重启 Deployment
# ============================================================
@tool
def kubectl_restart_deployment(deployment_name: str, namespace: str = "default") -> dict:
    """滚动重启 Kubernetes Deployment

    触发 Deployment 的 rollout restart 以重启所有 Pod（滚动更新）。
    **这是一个修改操作**，需要 KUBERNETES_ALLOW_RESTART=true 配置。

    Args:
        deployment_name: Deployment 名称
        namespace: Deployment 所在命名空间，默认 default
    """
    if not K8S_ALLOW_RESTART:
        return {
            "success": False,
            "error": "滚动重启操作未启用（KUBERNETES_ALLOW_RESTART=false）。"
                     "如需启用，请设置环境变量 KUBERNETES_ALLOW_RESTART=true。",
        }

    args = ["rollout", "restart", "deployment", deployment_name, "-n", namespace]
    result = _run_kubectl(args)

    if not result.get("success"):
        return result

    return {
        "success": True,
        "deployment": deployment_name,
        "namespace": namespace,
        "message": f"Deployment '{deployment_name}' 滚动重启已触发。",
    }
