"""系统指标采集器

定时采集系统资源指标并更新 Prometheus Gauge。
"""

import logging
import threading
from typing import Optional

import psutil

from app.monitoring.metrics import (
    cpu_usage_gauge,
    memory_usage_gauge,
    disk_usage_gauge,
    docker_containers_total,
    docker_containers_running,
)

logger = logging.getLogger(__name__)

_HOST_LABEL = "localhost"


def collect_system_metrics():
    """采集系统 CPU / 内存 / 磁盘指标"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_usage_gauge.labels(host=_HOST_LABEL).set(cpu_percent)

        # 内存
        mem = psutil.virtual_memory()
        memory_usage_gauge.labels(host=_HOST_LABEL).set(mem.percent)

        # 磁盘
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage_gauge.labels(
                    host=_HOST_LABEL,
                    mount=partition.mountpoint,
                ).set(usage.percent)
            except PermissionError:
                continue

        logger.debug("系统指标采集完成: CPU=%s%%, 内存=%s%%", cpu_percent, mem.percent)
        return True
    except Exception as e:
        logger.warning("系统指标采集失败: %s", e)
        return False


def collect_docker_metrics():
    """采集 Docker 容器指标"""
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(all=True)
        total = len(containers)
        running = len([c for c in containers if c.status == "running"])
        docker_containers_total.labels(host=_HOST_LABEL).set(total)
        docker_containers_running.labels(host=_HOST_LABEL).set(running)
        return True
    except Exception as e:
        logger.debug("Docker 指标采集失败（可能未安装 Docker）: %s", e)
        return False


def collect_all_metrics():
    """采集所有指标"""
    results = []
    results.append(collect_system_metrics())
    results.append(collect_docker_metrics())
    return all(results)


# ============================================================
# 定时采集线程
# ============================================================
class MetricsCollectorThread(threading.Thread):
    """后台定时指标采集线程"""

    def __init__(self, interval: int = 15, daemon: bool = True):
        super().__init__(name="metrics-collector", daemon=daemon)
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        logger.info("指标采集线程启动 (间隔=%ds)", self.interval)
        while not self._stop_event.is_set():
            try:
                collect_all_metrics()
            except Exception as e:
                logger.error("指标采集异常: %s", e)
            self._stop_event.wait(self.interval)

    def stop(self):
        self._stop_event.set()
        logger.info("指标采集线程已停止")


_collector_thread: Optional[MetricsCollectorThread] = None


def start_collector(interval: int = 15):
    """启动后台指标采集"""
    global _collector_thread
    if _collector_thread and _collector_thread.is_alive():
        logger.info("指标采集线程已在运行")
        return
    _collector_thread = MetricsCollectorThread(interval=interval)
    _collector_thread.start()


def stop_collector():
    """停止后台指标采集"""
    global _collector_thread
    if _collector_thread:
        _collector_thread.stop()
        _collector_thread.join(timeout=5)
        _collector_thread = None
