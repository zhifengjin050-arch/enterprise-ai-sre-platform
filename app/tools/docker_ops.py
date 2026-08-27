"""Docker 操作工具

使用 Docker SDK for Python 获取 Docker 状态和容器日志。
所有操作均为只读。
"""

import logging

from langchain.tools import tool

logger = logging.getLogger("agent")


def _get_docker_client():
    """获取 Docker 客户端，优雅处理 Docker 不可用情况"""
    try:
        import docker
        return docker.from_env()
    except Exception:
        return None


@tool
def docker_status() -> list[dict] | str:
    """获取所有 Docker 容器的运行状态"""
    client = _get_docker_client()
    if client is None:
        return "Docker 服务未启动或不可用，请检查 Docker 是否已安装并运行。"

    try:
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            result.append({
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else "N/A",
                "ports": list(c.ports.keys()) if c.ports else [],
                "created": c.attrs.get("Created", ""),
            })
        if not result:
            return "当前没有 Docker 容器。"
        return result
    except Exception as e:
        return f"获取 Docker 状态失败: {str(e)}"


@tool
def docker_logs(container_name: str, tail: int = 100) -> str:
    """获取指定 Docker 容器的最近日志

    Args:
        container_name: 容器名称或 ID
        tail: 获取最近多少行日志，默认 100
    """
    client = _get_docker_client()
    if client is None:
        return "Docker 服务未启动或不可用。"

    try:
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail, timestamps=True)
        decoded = logs.decode("utf-8", errors="replace")
        return decoded if decoded else f"容器 {container_name} 没有日志输出。"
    except Exception as e:
        err_msg = str(e)
        if "NotFound" in type(e).__name__ or "not found" in err_msg.lower():
            return f"容器 '{container_name}' 不存在。请先使用 docker_status 查看可用容器列表。"
        logger.warning("获取容器日志失败: %s", err_msg)
        return f"获取容器日志失败: {err_msg}"
