"""测试可观测性监控模块

测试覆盖：
- 指标注册与 Prometheus 格式输出
- HTTP 请求指标记录
- Agent 执行指标记录
- 系统指标采集
- 指标采集线程
"""

import pytest
import time
import json
import threading
from unittest.mock import patch, MagicMock


# ============================================================
# 测试组1：指标注册与输出
# ============================================================
class TestMetricsRegistration:
    def test_metrics_module_imports(self):
        """验证指标模块可以正常导入"""
        from app.monitoring.metrics import (
            get_metrics, http_requests_total, cpu_usage_gauge,
            agent_requests_total, agent_success_total, agent_errors_total,
        )
        assert get_metrics is not None
        assert http_requests_total is not None
        assert cpu_usage_gauge is not None
        assert agent_requests_total is not None
        assert agent_success_total is not None
        assert agent_errors_total is not None

    def test_get_metrics_returns_prometheus_format(self):
        """验证 get_metrics 返回 Prometheus 文本格式"""
        from app.monitoring.metrics import get_metrics
        output = get_metrics()
        assert isinstance(output, str)
        assert len(output) > 0
        # Prometheus 格式特征
        assert "# HELP" in output or "devops_" in output

    def test_http_metrics_record(self):
        """验证 HTTP 请求指标记录"""
        from app.monitoring.metrics import record_http_request
        record_http_request("GET", "/test", 200, 0.1)
        record_http_request("POST", "/api/chat", 200, 0.5)

    def test_agent_metrics_record(self):
        """验证 Agent 执行指标记录"""
        from app.monitoring.metrics import observe_agent_execution, observe_llm_request, record_tool_call
        observe_agent_execution(duration=2.5, success=True, tools_called=3)
        observe_agent_execution(duration=0.5, success=False, tools_called=0)
        observe_llm_request(duration=1.2)
        record_tool_call("server_health")
        record_tool_call("docker_status")


# ============================================================
# 测试组2：系统指标采集
# ============================================================
class TestMetricsCollector:
    def test_collect_system_metrics(self):
        """验证系统指标采集函数可以执行"""
        from app.monitoring.collector import collect_system_metrics
        result = collect_system_metrics()
        # Docker 采集可能失败，但系统采集应成功
        assert result is True

    def test_collect_docker_metrics_graceful_fail(self):
        """验证 Docker 指标采集失败时不会抛出异常"""
        from app.monitoring.collector import collect_docker_metrics
        # 不管有没有 Docker，都不应该抛异常
        result = collect_docker_metrics()
        assert result in (True, False)

    def test_collect_all_metrics(self):
        """验证全量采集不会报错"""
        from app.monitoring.collector import collect_all_metrics
        result = collect_all_metrics()
        assert isinstance(result, bool)


# ============================================================
# 测试组3：指标采集线程
# ============================================================
class TestMetricsCollectorThread:
    def test_start_stop_collector(self):
        """验证指标采集线程启动和停止"""
        from app.monitoring.collector import start_collector, stop_collector
        start_collector(interval=60)
        # 启动两次不应报错
        start_collector(interval=60)
        stop_collector()
        # 停止两次不应报错
        stop_collector()

    def test_collector_thread_running(self):
        """验证采集线程正常运行后标记"""
        from app.monitoring.collector import start_collector, stop_collector
        start_collector(interval=60)
        from app.monitoring.collector import _collector_thread
        assert _collector_thread is not None, "采集线程应该已创建"
        assert _collector_thread.is_alive()
        stop_collector()


# ============================================================
# 测试组4：Prometheus 配置
# ============================================================
class TestPrometheusConfig:
    def test_prometheus_yml_exists(self):
        """验证 prometheus.yml 存在且包含必要配置"""
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prometheus", "prometheus.yml")
        assert os.path.exists(config_path), "prometheus.yml 文件不存在"
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "scrape_configs" in content
        assert "ai-devops-backend" in content
        assert "metrics_path: \"/metrics\"" in content or "metrics_path" in content

    def test_alerts_yml_exists(self):
        """验证 alerts.yml 存在且包含告警规则"""
        import os
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prometheus", "alerts.yml")
        assert os.path.exists(config_path), "alerts.yml 文件不存在"
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "groups" in content
        assert "alert" in content
        assert "HighCPULoad" in content or "devops_cpu" in content


# ============================================================
# 测试组5：Metrics 配置兼容性
# ============================================================
class TestMetricsConfig:
    def test_settings_include_monitoring(self):
        """验证系统配置包含监控相关字段"""
        from app.config import settings
        assert hasattr(settings, "metrics_collect_interval")
        assert hasattr(settings, "alert_evaluate_interval")
        assert hasattr(settings, "feishu_webhook_url")
        assert hasattr(settings, "dingtalk_webhook_url")
        assert hasattr(settings, "wechat_webhook_url")

    def test_metrics_endpoint_enabled(self):
        """验证 main.py 中存在 /metrics 路由"""
        import inspect
        from app.main import app
        route_paths = []
        for r in app.routes:
            try:
                route_paths.append(r.path)
            except AttributeError:
                pass
        assert "/metrics" in route_paths

    def test_env_example_includes_monitoring(self):
        """验证 .env.example 包含监控配置项"""
        import os
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
        assert os.path.exists(env_path)
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "METRICS_COLLECT_INTERVAL" in content
        assert "ALERT_EVALUATE_INTERVAL" in content
        assert "FEISHU_WEBHOOK_URL" in content or "feishu" in content.lower()