"""Kubernetes 运维工具

使用 kubectl 命令获取 Kubernetes 集群信息（只读操作）。
"""

import subprocess
from langchain.tools import tool


def _run_kubectl(args: list[str], timeout: int = 15) -> str:
    """执行 kubectl 命令并返回输出"""
    try:
        cmd = ["kubectl"] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return f"kubectl 执行失败: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "未找到 kubectl 命令，请确认已安装 Kubernetes 命令行工具。"
    except subprocess.TimeoutExpired:
        return "kubectl 命令执行超时。"
    except Exception as e:
        return f"kubectl 执行异常: {str(e)}"


@tool
def k8s_pods(namespace: str = "default") -> str:
    """获取 Kubernetes Pod 列表

    Args:
        namespace: Kubernetes 命名空间，默认为 default
    """
    output = _run_kubectl(["get", "pods", "-n", namespace, "-o", "wide"])
    if not output:
        return f"命名空间 '{namespace}' 下没有 Pod。"
    return output


@tool
def k8s_deployments(namespace: str = "default") -> str:
    """获取 Kubernetes Deployment 列表

    Args:
        namespace: Kubernetes 命名空间，默认为 default
    """
    output = _run_kubectl(["get", "deployments", "-n", namespace, "-o", "wide"])
    if not output:
        return f"命名空间 '{namespace}' 下没有 Deployment。"
    return output


@tool
def k8s_services(namespace: str = "default") -> str:
    """获取 Kubernetes Service 列表

    Args:
        namespace: Kubernetes 命名空间，默认为 default
    """
    output = _run_kubectl(["get", "services", "-n", namespace, "-o", "wide"])
    if not output:
        return f"命名空间 '{namespace}' 下没有 Service。"
    return output


@tool
def k8s_pod_logs(pod_name: str, namespace: str = "default", tail: int = 50) -> str:
    """获取指定 Pod 的日志

    Args:
        pod_name: Pod 名称
        namespace: Kubernetes 命名空间，默认为 default
        tail: 返回最近多少行日志，默认 50
    """
    output = _run_kubectl(["logs", pod_name, "-n", namespace, f"--tail={tail}"])
    if not output:
        return f"Pod '{pod_name}' 没有日志输出。"
    return output