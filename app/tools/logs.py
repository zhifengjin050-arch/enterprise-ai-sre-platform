"""系统日志查询工具

在 Linux 环境下使用 journalctl 查询系统日志。
在 Windows 环境下返回友好提示。
所有操作均为只读。
"""

import platform
import subprocess
from langchain.tools import tool


def _is_linux() -> bool:
    return platform.system().lower() == "linux"


@tool
def system_logs(service: str = "", level: str = "ERROR", lines: int = 50) -> str:
    """查询系统日志

    在 Linux 上使用 journalctl 查询系统日志；
    在 Windows 上提示不支持。

    Args:
        service: 服务名称（如 nginx、ssh），可选
        level: 日志级别（ERROR、WARNING、INFO），默认 ERROR
        lines: 返回最近多少行，默认 50
    """
    if not _is_linux():
        return "当前环境不支持 journalctl 系统日志查询（仅在 Linux 上可用）。"

    try:
        cmd = ["journalctl", "--no-pager", "-n", str(lines), "-p", level]
        if service:
            cmd.extend(["-u", service])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return f"journalctl 执行失败: {result.stderr.strip()}"

        output = result.stdout.strip()
        if not output:
            service_str = f" 服务 '{service}'" if service else ""
            return f"未找到{service_str} 级别为 {level} 的日志。"
        return output

    except subprocess.TimeoutExpired:
        return "日志查询超时（10 秒），请尝试减少查询行数。"
    except FileNotFoundError:
        return "系统未找到 journalctl 命令，请确认 systemd 是否可用。"
    except Exception as e:
        return f"日志查询异常: {str(e)}"
