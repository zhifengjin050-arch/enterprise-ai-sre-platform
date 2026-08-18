"""MCP / 内置工具安全元数据（不改变工具执行逻辑）。

供 Agent 审批与 RBAC 决策使用。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    description: str
    category: str
    risk_level: str  # safe | moderate | dangerous
    required_permission: str
    audit_required: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _m(name, description, category, risk_level, required_permission, audit_required) -> ToolMetadata:
    return ToolMetadata(name, description, category, risk_level, required_permission, audit_required)


# Project2 MCP Server 17 tools + 常用内置别名
TOOL_METADATA: dict[str, ToolMetadata] = {
    # System — safe
    "get_server_health": _m("get_server_health", "采集服务器综合健康状态", "system", "safe", "devops.viewer", False),
    "get_system_info": _m("get_system_info", "获取操作系统与主机信息", "system", "safe", "devops.viewer", False),
    "get_cpu_usage": _m("get_cpu_usage", "读取 CPU 使用率", "system", "safe", "devops.viewer", False),
    "get_memory_usage": _m("get_memory_usage", "读取内存使用率", "system", "safe", "devops.viewer", False),
    "get_disk_usage": _m("get_disk_usage", "读取磁盘使用率", "system", "safe", "devops.viewer", False),
    "get_audit_logs": _m("get_audit_logs", "读取审计日志", "system", "moderate", "devops.admin", True),
    "list_processes": _m("list_processes", "列出高占用进程", "system", "safe", "devops.viewer", False),
    # Docker
    "docker_list": _m("docker_list", "列出 Docker 容器", "docker", "safe", "devops.viewer", False),
    "docker_logs": _m("docker_logs", "读取容器日志", "docker", "safe", "devops.viewer", False),
    "docker_restart": _m("docker_restart", "重启 Docker 容器", "docker", "dangerous", "devops.admin", True),
    "docker_start": _m("docker_start", "启动 Docker 容器", "docker", "dangerous", "devops.admin", True),
    "docker_stop": _m("docker_stop", "停止 Docker 容器", "docker", "dangerous", "devops.admin", True),
    # Kubernetes
    "k8s_get_pods": _m("k8s_get_pods", "列出 Pod", "kubernetes", "safe", "devops.viewer", False),
    "k8s_get_deployments": _m("k8s_get_deployments", "列出 Deployment", "kubernetes", "safe", "devops.viewer", False),
    "k8s_get_services": _m("k8s_get_services", "列出 Service", "kubernetes", "safe", "devops.viewer", False),
    "k8s_logs": _m("k8s_logs", "读取 Pod 日志", "kubernetes", "safe", "devops.viewer", False),
    "k8s_restart_deployment": _m("k8s_restart_deployment", "滚动重启 Deployment", "kubernetes", "dangerous", "devops.admin", True),
    "kubectl_restart_deployment": _m("kubectl_restart_deployment", "滚动重启 Deployment", "kubernetes", "dangerous", "devops.admin", True),
    "kubectl_delete_pod": _m("kubectl_delete_pod", "删除 Pod", "kubernetes", "dangerous", "devops.admin", True),
    # SSH
    "ssh_check_connection": _m("ssh_check_connection", "检测 SSH 连通性", "ssh", "safe", "devops.viewer", False),
    "ssh_execute_command": _m("ssh_execute_command", "远程执行命令", "ssh", "dangerous", "devops.admin", True),
    "ssh_upload_file": _m("ssh_upload_file", "上传文件到远程主机", "ssh", "dangerous", "devops.admin", True),
}


def get_tool_metadata(name: str) -> Optional[ToolMetadata]:
    return TOOL_METADATA.get(name)


def list_tool_metadata() -> list[dict]:
    return [m.to_dict() for m in TOOL_METADATA.values()]


def requires_approval(name: str) -> bool:
    meta = get_tool_metadata(name)
    if meta:
        return meta.risk_level == "dangerous" or meta.audit_required
    return True
