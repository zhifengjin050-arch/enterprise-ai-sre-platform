"""SSH 远程运维工具

使用 paramiko 通过 SSH 连接远程服务器执行运维命令。
所有操作均为只读（仅执行查询类命令）。
"""

import logging
import paramiko
from langchain.tools import tool

logger = logging.getLogger("agent")

# 全局 SSH 客户端缓存（避免重复连接）
_ssh_clients: dict[str, paramiko.SSHClient] = {}


def _get_ssh_client(host: str, port: int, username: str, password: str | None = None, key_file: str | None = None) -> paramiko.SSHClient:
    """获取 SSH 客户端（带缓存）

    Args:
        host: 服务器地址
        port: SSH 端口
        username: 登录用户名
        password: 密码（可选）
        key_file: 密钥文件路径（可选）

    Returns:
        SSHClient 实例
    """
    cache_key = f"{host}:{port}:{username}"
    if cache_key in _ssh_clients and _ssh_clients[cache_key].get_transport() is not None and _ssh_clients[cache_key].get_transport().is_active():
        return _ssh_clients[cache_key]

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_file:
            client.connect(host, port=port, username=username, key_filename=key_file, timeout=10)
        else:
            client.connect(host, port=port, username=username, password=password, timeout=10)
        _ssh_clients[cache_key] = client
        return client
    except Exception as e:
        logger.error("SSH 连接失败 %s:%d - %s", host, port, e)
        raise


def _close_ssh(host: str, port: int, username: str):
    """关闭 SSH 连接"""
    cache_key = f"{host}:{port}:{username}"
    client = _ssh_clients.pop(cache_key, None)
    if client:
        try:
            client.close()
        except Exception:
            pass


def _lookup_server(server_name: str) -> dict:
    """根据服务器名称查找服务器信息

    通过数据库查询 ManagedServer 记录。
    """
    from app.database.session import get_local_session
    from app.database.models import ManagedServer

    session = get_local_session()
    try:
        server = session.query(ManagedServer).filter(
            ManagedServer.name == server_name,
            ManagedServer.is_active == True,
        ).first()
        if server is None:
            raise ValueError(f"未找到名为 '{server_name}' 的活跃服务器，请先在 /api/servers 中注册。")
        return {
            "host": server.host,
            "port": server.port,
            "username": server.username,
            "password": server.auth_credential if server.auth_type == "password" else None,
            "key_file": server.auth_credential if server.auth_type == "key" else None,
        }
    finally:
        session.close()


def _exec_ssh_command(server_name: str, command: str, timeout: int = 30) -> str:
    """通过 SSH 在远程服务器上执行命令

    Args:
        server_name: 服务器名称（在 ManagedServer 中注册的名称）
        command: 要执行的命令
        timeout: 超时时间（秒）

    Returns:
        命令输出
    """
    try:
        server_info = _lookup_server(server_name)
        client = _get_ssh_client(
            host=server_info["host"],
            port=server_info["port"],
            username=server_info["username"],
            password=server_info.get("password"),
            key_file=server_info.get("key_file"),
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()

        output = stdout.read().decode("utf-8", errors="replace").strip()
        error_output = stderr.read().decode("utf-8", errors="replace").strip()

        if exit_code != 0:
            logger.warning("SSH 命令执行失败 (exit=%d): %s", exit_code, command[:100])
            return f"命令执行失败 (退出码: {exit_code})\n标准错误:\n{error_output}"

        return output if output else "命令执行成功，无输出。"

    except ValueError as e:
        return str(e)
    except paramiko.AuthenticationException:
        return f"SSH 认证失败: 无法连接到服务器 '{server_name}'，请检查用户名和密码/密钥。"
    except paramiko.SSHException as e:
        return f"SSH 连接错误: {e}"
    except Exception as e:
        return f"SSH 执行异常: {str(e)}"


@tool
def ssh_exec(server_name: str, command: str) -> str:
    """在远程服务器上执行任意命令（只读查询）

    连接到已注册的远程服务器，执行指定的 Shell 命令并返回结果。
    只能用于查询类操作，不可用于修改系统配置。

    Args:
        server_name: 服务器名称（需在 /api/servers 中预先注册）
        command: 要执行的 Shell 命令（仅限查询类命令）
    """
    logger.info("SSH 执行: server=%s command=%s", server_name, command[:80])
    return _exec_ssh_command(server_name, command, timeout=30)


@tool
def ssh_server_health(server_name: str) -> str:
    """获取远程服务器的健康状态（CPU、内存、磁盘）

    通过 SSH 连接到远程服务器，执行系统命令采集 CPU、内存、磁盘信息。

    Args:
        server_name: 服务器名称（需在 /api/servers 中预先注册）
    """
    command = (
        "echo '=== CPU ===' && "
        "cat /proc/loadavg && "
        "echo '=== MEMORY ===' && "
        "free -h && "
        "echo '=== DISK ===' && "
        "df -h / && "
        "echo '=== UPTIME ===' && "
        "uptime"
    )
    return _exec_ssh_command(server_name, command, timeout=15)


@tool
def ssh_docker_status(server_name: str) -> str:
    """获取远程服务器的 Docker 容器状态

    通过 SSH 连接到远程服务器，列出所有 Docker 容器。

    Args:
        server_name: 服务器名称（需在 /api/servers 中预先注册）
    """
    command = "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'"
    result = _exec_ssh_command(server_name, command, timeout=15)
    if "无法连接到" in result or "认证失败" in result:
        return result
    return "## Docker 容器状态\n\n```\n" + result + "\n```" if result != "命令执行成功，无输出。" else "远程服务器上未安装 Docker 或无容器运行。"


@tool
def ssh_docker_logs(server_name: str, container_name: str, tail: int = 50) -> str:
    """获取远程服务器上指定 Docker 容器的日志

    通过 SSH 连接到远程服务器，获取容器日志。

    Args:
        server_name: 服务器名称（需在 /api/servers 中预先注册）
        container_name: 容器名称或 ID
        tail: 获取最近多少行日志，默认 50
    """
    command = f"docker logs --tail {tail} --timestamps {container_name} 2>&1"
    return _exec_ssh_command(server_name, command, timeout=15)


@tool
def ssh_system_logs(server_name: str, service: str = "", level: str = "ERROR", lines: int = 50) -> str:
    """获取远程服务器的系统日志

    通过 SSH 连接到远程服务器，使用 journalctl 查询系统日志。

    Args:
        server_name: 服务器名称（需在 /api/servers 中预先注册）
        service: 服务名称（如 nginx, sshd），可选
        level: 日志级别（emerg, alert, crit, err, warning, info），默认 err
        lines: 返回最近多少行，默认 50
    """
    cmd = ["journalctl", "--no-pager", "-n", str(lines), "-p", level]
    if service:
        cmd.extend(["-u", service])
    command = " ".join(cmd) + " 2>&1"
    result = _exec_ssh_command(server_name, command, timeout=15)
    if "未找到" in result or "journalctl" in result:
        # 尝试使用 dmesg 作为备选
        alt_command = f"dmesg | tail -{lines}"
        return _exec_ssh_command(server_name, alt_command, timeout=15)
    return result


def close_all_ssh_connections():
    """关闭所有 SSH 连接（用于应用关闭时清理）"""
    global _ssh_clients
    for key, client in _ssh_clients.items():
        try:
            client.close()
        except Exception:
            pass
    _ssh_clients = {}