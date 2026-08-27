"""测试智能告警系统

测试覆盖：
- 告警规则引擎
- 告警管理器
- 通知渠道（包含模拟）
- AI 告警分析
- Docker Compose 集成验证
"""

import pytest
import time
from unittest.mock import patch, MagicMock


# ============================================================
# 测试组1：告警规则
# ============================================================
class TestAlertRules:
    def test_rules_defined(self):
        """验证默认规则列表已定义"""
        from app.alert.rules import DEFAULT_RULES
        assert len(DEFAULT_RULES) >= 3
        rule_names = [r.name for r in DEFAULT_RULES]
        assert "cpu_high" in rule_names
        assert "memory_high" in rule_names
        assert "disk_high" in rule_names

    def test_rule_structure(self):
        """验证规则结构包含必要字段"""
        from app.alert.rules import AlertRule, DEFAULT_RULES
        rule = DEFAULT_RULES[0]
        assert hasattr(rule, "name")
        assert hasattr(rule, "description")
        assert hasattr(rule, "severity")
        assert hasattr(rule, "check_fn")
        assert hasattr(rule, "cooldown_seconds")
        assert rule.cooldown_seconds > 0

    def test_cpu_rule_check(self):
        """验证 CPU 规则检查函数可执行"""
        from app.alert.rules import _check_cpu_high
        result = _check_cpu_high()
        # 返回 None（正常）或 字符串（告警触发），不应抛异常
        assert result is None or isinstance(result, str)

    def test_memory_rule_check(self):
        """验证内存规则检查函数可执行"""
        from app.alert.rules import _check_memory_high
        result = _check_memory_high()
        assert result is None or isinstance(result, str)

    def test_disk_rule_check(self):
        """验证磁盘规则检查函数可执行"""
        from app.alert.rules import _check_disk_high
        result = _check_disk_high()
        assert result is None or isinstance(result, str)


# ============================================================
# 测试组2：告警管理器
# ============================================================
class TestAlertManager:
    def test_alert_evaluate(self):
        """验证告警评估函数可执行"""
        from app.alert.manager import evaluate_rules
        alerts = evaluate_rules()
        assert isinstance(alerts, list)

    def test_get_alerts(self):
        """验证获取告警列表"""
        from app.alert.manager import get_alerts
        alerts = get_alerts()
        assert isinstance(alerts, list)

    def test_get_alerts_with_status_filter(self):
        """验证带状态过滤的告警查询"""
        from app.alert.manager import get_alerts
        firing = get_alerts(status="firing")
        resolved = get_alerts(status="resolved")
        assert isinstance(firing, list)
        assert isinstance(resolved, list)

    def test_resolve_alert_existing(self):
        """验证关闭存在的告警"""
        from app.alert.manager import get_alerts, resolve_alert
        alerts = get_alerts()
        if alerts:
            alert_id = alerts[-1]["id"]
            result = resolve_alert(alert_id)
            assert result is True

    def test_resolve_alert_not_exist(self):
        """验证关闭不存在的告警返回 False"""
        from app.alert.manager import resolve_alert
        result = resolve_alert(99999)
        assert result is False


# ============================================================
# 测试组3：通知渠道
# ============================================================
class TestNotificationChannels:
    def test_database_channel(self):
        """验证数据库通知渠道"""
        from app.alert.channels import DatabaseChannel
        channel = DatabaseChannel()
        result = channel.send("测试告警", "测试消息", "warning")
        assert result is True

    def test_feishu_channel_no_url(self):
        """验证飞书渠道无 URL 时不发送"""
        from app.alert.channels import FeishuWebhookChannel
        channel = FeishuWebhookChannel("")
        result = channel.send("测试", "消息", "warning")
        assert result is False

    def test_dingtalk_channel_no_url(self):
        """验证钉钉渠道无 URL 时不发送"""
        from app.alert.channels import DingTalkWebhookChannel
        channel = DingTalkWebhookChannel("")
        result = channel.send("测试", "消息", "warning")
        assert result is False

    def test_wechat_channel_no_url(self):
        """验证企业微信渠道无 URL 时不发送"""
        from app.alert.channels import WeChatWorkWebhookChannel
        channel = WeChatWorkWebhookChannel("")
        result = channel.send("测试", "消息", "warning")
        assert result is False

    def test_create_channels_default(self):
        """验证默认创建至少包含数据库渠道"""
        from app.alert.channels import create_channels, DatabaseChannel
        channels = create_channels()
        assert len(channels) >= 1
        assert any(isinstance(c, DatabaseChannel) for c in channels)


# ============================================================
# 测试组4：AI 告警分析
# ============================================================
class TestAlertAIAnalysis:
    def test_ai_analyze_without_llm(self):
        """验证无 LLM 配置时 AI 分析返回 None"""
        from app.alert.manager import ai_analyze_alert
        alert = {"title": "CPU 过高", "level": "warning", "message": "CPU 95%"}
        result = ai_analyze_alert(alert)
        # 如果没有配置 API Key，返回 None
        assert result is None or isinstance(result, str)


# ============================================================
# 测试组5：告警评估线程
# ============================================================
class TestAlertEvaluatorThread:
    def test_start_stop_evaluator(self):
        """验证告警评估线程启动和停止"""
        from app.alert.manager import start_alert_evaluator, stop_alert_evaluator
        start_alert_evaluator(interval=60)
        start_alert_evaluator(interval=60)  # 重复启动不应报错
        stop_alert_evaluator()
        stop_alert_evaluator()  # 重复停止不应报错


# ============================================================
# 测试组6：Docker Compose 集成
# ============================================================
class TestDockerComposeIntegration:
    def test_docker_compose_has_prometheus(self):
        """验证 docker-compose.yml 包含 Prometheus 服务"""
        import os
        compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
        assert os.path.exists(compose_path)
        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "prometheus:" in content
        assert "prom/prometheus" in content

    def test_docker_compose_has_grafana(self):
        """验证 docker-compose.yml 包含 Grafana 服务"""
        import os
        compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
        assert os.path.exists(compose_path)
        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "grafana:" in content
        assert "grafana/grafana" in content

    def test_grafana_dashboard_exists(self):
        """验证 Grafana Dashboard JSON 文件存在"""
        import os
        dash_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "grafana", "dashboards", "ai-devops-overview.json")
        assert os.path.exists(dash_path)
        import json
        with open(dash_path, "r", encoding="utf-8") as f:
            dashboard = json.load(f)
        assert "title" in dashboard
        assert "panels" in dashboard
        assert len(dashboard["panels"]) > 0

    def test_grafana_datasource_exists(self):
        """验证 Grafana 数据源配置存在"""
        import os
        ds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "grafana", "datasources", "datasources.yml")
        assert os.path.exists(ds_path)
        with open(ds_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Prometheus" in content
        assert "prometheus:9090" in content
