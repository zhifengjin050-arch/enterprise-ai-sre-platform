"""告警规则引擎

定义内置告警规则，支持自定义阈值。
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """告警规则定义"""
    name: str
    description: str
    severity: str  # "info" | "warning" | "critical"
    check_fn: Callable[[], Optional[str]]  # 返回 None 表示正常，返回消息表示触发
    cooldown_seconds: int = 300  # 冷却时间（防止重复告警）


# ============================================================
# 内置规则
# ============================================================

def _check_cpu_high() -> Optional[str]:
    """CPU 持续高于阈值"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    if cpu_percent > 90:
        return f"CPU 使用率过高: {cpu_percent:.1f}% (> 90%)"
    if cpu_percent > 80:
        return f"CPU 使用率偏高: {cpu_percent:.1f}% (> 80%)"
    return None


def _check_memory_high() -> Optional[str]:
    """内存使用率过高"""
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        return f"内存使用率过高: {mem.percent:.1f}% (> 90%)"
    if mem.percent > 85:
        return f"内存使用率偏高: {mem.percent:.1f}% (> 85%)"
    return None


def _check_disk_high() -> Optional[str]:
    """磁盘使用率过高"""
    alerts = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            if usage.percent > 90:
                alerts.append(f"磁盘 {partition.mountpoint} 使用率 {usage.percent:.1f}% (> 90%)")
            elif usage.percent > 85:
                alerts.append(f"磁盘 {partition.mountpoint} 使用率 {usage.percent:.1f}% (> 85%)")
        except PermissionError:
            continue
    return "\n".join(alerts) if alerts else None


def _check_docker_status() -> Optional[str]:
    """检查 Docker 是否有异常容器"""
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(all=True)
        unhealthy = [c for c in containers if c.status == "exited" or "unhealthy" in (c.attrs.get("State", {}).get("Health", {}).get("Status", ""))]
        if unhealthy:
            names = ", ".join(c.name for c in unhealthy[:5])
            return f"发现 {len(unhealthy)} 个异常容器: {names}"
    except Exception:
        pass
    return None


# ============================================================
# 默认规则列表
# ============================================================
DEFAULT_RULES: list[AlertRule] = [
    AlertRule(
        name="cpu_high",
        description="CPU 使用率过高",
        severity="warning",
        check_fn=_check_cpu_high,
        cooldown_seconds=300,
    ),
    AlertRule(
        name="memory_high",
        description="内存使用率过高",
        severity="warning",
        check_fn=_check_memory_high,
        cooldown_seconds=300,
    ),
    AlertRule(
        name="disk_high",
        description="磁盘使用率过高",
        severity="warning",
        check_fn=_check_disk_high,
        cooldown_seconds=600,
    ),
    AlertRule(
        name="docker_unhealthy",
        description="Docker 异常容器检测",
        severity="critical",
        check_fn=_check_docker_status,
        cooldown_seconds=600,
    ),
]
