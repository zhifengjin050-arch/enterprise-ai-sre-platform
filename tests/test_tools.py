"""工具层测试"""

import sys
import json


def test_server_health() -> None:
    """测试 server_health 工具"""
    from app.tools.server_health import server_health

    result = server_health.invoke({})

    assert isinstance(result, dict), "应返回 dict"
    assert "cpu" in result, "应包含 cpu 字段"
    assert "memory" in result, "应包含 memory 字段"
    assert "disks" in result, "应包含 disks 字段"

    cpu = result["cpu"]
    assert isinstance(cpu["percent"], (int, float)), "CPU percent 应可转换为数字"
    assert cpu["cores"] > 0, "CPU 核心数应大于 0"

    mem = result["memory"]
    assert isinstance(mem["percent"], (int, float)), "内存 percent 应可转换为数字"
    assert mem["total_gb"] > 0, "内存总量应大于 0"

    disks = result["disks"]
    assert isinstance(disks, list), "disks 应为列表"

    print("[OK] server_health 正常返回")
    print(f"      CPU: {cpu['percent']}% ({cpu['cores']} cores)")
    print(f"      内存: {mem['percent']}% ({mem['used_gb']}/{mem['total_gb']} GB)")
    print(f"      磁盘: {len(disks)} 个分区")


def test_docker_status() -> None:
    """测试 docker_status 工具（处理 Docker 不可用情况）"""
    from app.tools.docker_ops import docker_status

    result = docker_status.invoke({})

    # Docker 可能不可用，但工具不应抛出异常
    assert result is not None, "不应返回 None"

    if isinstance(result, str):
        print(f"[OK] docker_status 正常处理 (Docker 不可用: {result})")
    else:
        assert isinstance(result, list), "应返回列表"
        print(f"[OK] docker_status 正常返回 ({len(result)} 个容器)")


def test_docker_logs() -> None:
    """测试 docker_logs 工具（异常处理）"""
    from app.tools.docker_ops import docker_logs

    result = docker_logs.invoke({"container_name": "_nonexistent_test_container_"})

    # 容器不存在时应该返回友好错误消息，而不是抛出异常
    assert result is not None, "不应返回 None"
    assert "不存在" in result or "不可用" in result, "应返回友好错误信息"
    print("[OK] docker_logs 异常处理正常")


def test_system_logs() -> None:
    """测试 system_logs 工具（跨平台处理）"""
    from app.tools.logs import system_logs

    result = system_logs.invoke({"service": "nginx", "level": "ERROR", "lines": 50})

    assert result is not None, "不应返回 None"
    assert isinstance(result, str), "应返回字符串"

    # Windows 环境下返回友好提示，Linux 环境下正常执行
    print("[OK] system_logs 正常处理")
    if "不支持" in result:
        print("      (当前环境: Windows, 仅支持 Linux journalctl)")
    else:
        lines = result.count("\n") + 1
        print(f"      (返回 {lines} 行日志)")


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 60)
    print("工具层测试开始")
    print("=" * 60)

    test_server_health()
    test_docker_status()
    test_docker_logs()
    test_system_logs()

    print("=" * 60)
    print("全部测试通过")
    print("=" * 60)
