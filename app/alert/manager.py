"""告警管理器

负责规则评估、告警创建、通知分发和 AI 分析调度。
"""

import datetime
import json
import logging
import threading
import time
from typing import Optional

from app.config import settings
from app.alert.rules import DEFAULT_RULES, AlertRule
from app.alert.channels import create_channels, NotificationChannel

logger = logging.getLogger(__name__)

# 内存告警存储（生产环境应使用数据库）
_alerts: list[dict] = []
_last_fired: dict[str, float] = {}  # rule_name -> last_fired_timestamp

_channels: list[NotificationChannel] = []


def ensure_channels():
    """确保通知渠道已初始化"""
    global _channels
    if not _channels:
        _channels = create_channels()


def _create_alert(rule: AlertRule, message: str) -> dict:
    """创建告警对象"""
    now = datetime.datetime.utcnow()
    return {
        "id": len(_alerts) + 1,
        "level": rule.severity,
        "title": rule.name,
        "message": message,
        "source": rule.name,
        "status": "firing",
        "created_at": now.isoformat(),
        "resolved_at": None,
    }


def _send_notification(alert: dict):
    """发送告警通知到所有渠道"""
    ensure_channels()
    for channel in _channels:
        try:
            channel.send(alert["title"], alert["message"], alert["level"])
        except Exception as e:
            logger.warning("通知发送失败: %s", e)


def evaluate_rules() -> list[dict]:
    """评估所有规则，返回新触发的告警"""
    new_alerts = []
    now = time.monotonic()

    for rule in DEFAULT_RULES:
        try:
            message = rule.check_fn()
            if message is not None:
                # 冷却检查
                last = _last_fired.get(rule.name, 0)
                if now - last < rule.cooldown_seconds:
                    continue

                alert = _create_alert(rule, message)
                _alerts.append(alert)
                _last_fired[rule.name] = now
                new_alerts.append(alert)

                # 发送通知
                _send_notification(alert)
                logger.warning("[告警触发] %s: %s", rule.name, message[:200])
        except Exception as e:
            logger.error("规则评估异常 %s: %s", rule.name, e)

    return new_alerts


def get_alerts(status: Optional[str] = None, limit: int = 100) -> list[dict]:
    """获取告警列表"""
    alerts = _alerts
    if status:
        alerts = [a for a in alerts if a["status"] == status]
    return alerts[-limit:]


def resolve_alert(alert_id: int) -> bool:
    """关闭告警（标记为已解决）"""
    for alert in reversed(_alerts):
        if alert["id"] == alert_id:
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.datetime.utcnow().isoformat()
            logger.info("告警已关闭: id=%d title=%s", alert_id, alert["title"])
            return True
    return False


def ai_analyze_alert(alert: dict) -> Optional[str]:
    """调用 AI Agent 分析告警原因（简易版本）"""
    try:
        from app.llm.client import DeepSeekClient

        client = DeepSeekClient()
        if not client.is_configured:
            return None

        prompt = f"""你是一个 AI 运维专家，请分析以下告警：

告警标题：{alert['title']}
告警等级：{alert['level']}
告警消息：{alert['message']}

请输出 JSON 格式的分析报告：
{{
    "severity": "high/medium/low",
    "problem": "问题描述",
    "possible_reasons": ["可能原因1", "可能原因2"],
    "suggestions": ["建议1", "建议2"]
}}
"""
        response = client.chat([{"role": "user", "content": prompt}])
        return response
    except Exception as e:
        logger.warning("AI 告警分析失败: %s", e)
        return None


# ============================================================
# 后台告警评估线程
# ============================================================
class AlertEvaluatorThread(threading.Thread):
    """后台定时告警评估线程"""

    def __init__(self, interval: int = 30, daemon: bool = True):
        super().__init__(name="alert-evaluator", daemon=daemon)
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        logger.info("告警评估线程启动 (间隔=%ds)", self.interval)
        while not self._stop_event.is_set():
            try:
                new_alerts = evaluate_rules()
                if new_alerts:
                    logger.info("新触发 %d 条告警", len(new_alerts))
            except Exception as e:
                logger.error("告警评估异常: %s", e)
            self._stop_event.wait(self.interval)

    def stop(self):
        self._stop_event.set()
        logger.info("告警评估线程已停止")


_evaluator_thread: Optional[AlertEvaluatorThread] = None


def start_alert_evaluator(interval: int = 30):
    """启动后台告警评估"""
    global _evaluator_thread
    if _evaluator_thread and _evaluator_thread.is_alive():
        return
    _evaluator_thread = AlertEvaluatorThread(interval=interval)
    _evaluator_thread.start()


def stop_alert_evaluator():
    """停止后台告警评估"""
    global _evaluator_thread
    if _evaluator_thread:
        _evaluator_thread.stop()
        _evaluator_thread.join(timeout=5)
        _evaluator_thread = None