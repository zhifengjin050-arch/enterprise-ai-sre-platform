"""通知渠道

支持：
- 飞书 Webhook
- 钉钉 Webhook
- 企业微信 Webhook
- 数据库记录（兜底）
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    def send(self, title: str, message: str, severity: str) -> bool:
        """发送通知，返回是否成功"""
        ...


class DatabaseChannel(NotificationChannel):
    """数据库记录渠道（兜底）"""

    def send(self, title: str, message: str, severity: str) -> bool:
        """记录到数据库（由 alert manager 处理）"""
        logger.info("[告警记录] severity=%s title=%s message=%s", severity, title, message[:100])
        return True


class FeishuWebhookChannel(NotificationChannel):
    """飞书机器人 Webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, severity: str) -> bool:
        if not self.webhook_url:
            return False
        try:
            color_map = {"critical": "red", "warning": "yellow", "info": "blue"}
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": f"[{severity.upper()}] {title}"},
                        "template": color_map.get(severity, "blue"),
                    },
                    "elements": [
                        {"tag": "markdown", "content": message},
                        {"tag": "hr"},
                        {"tag": "note", "elements": [{"tag": "plain_text", "content": "AI DevOps Agent 告警系统"}]},
                    ],
                },
            }
            resp = httpx.post(self.webhook_url, json=payload, timeout=10)
            logger.info("飞书通知发送: status=%s", resp.status_code)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("飞书通知发送失败: %s", e)
            return False


class DingTalkWebhookChannel(NotificationChannel):
    """钉钉机器人 Webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, severity: str) -> bool:
        if not self.webhook_url:
            return False
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"[{severity.upper()}] {title}",
                    "text": f"### [{severity.upper()}] {title}\n\n{message}\n\n---\n*AI DevOps Agent 告警系统*",
                },
            }
            resp = httpx.post(self.webhook_url, json=payload, timeout=10)
            logger.info("钉钉通知发送: status=%s", resp.status_code)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("钉钉通知发送失败: %s", e)
            return False


class WeChatWorkWebhookChannel(NotificationChannel):
    """企业微信机器人 Webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, title: str, message: str, severity: str) -> bool:
        if not self.webhook_url:
            return False
        try:
            color_map = {"critical": "red", "warning": "yellow", "info": "gray"}
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### [{severity.upper()}] <font color=\"{color_map.get(severity, 'gray')}\">{title}</font>\n{message}\n\n---\nAI DevOps Agent 告警系统",
                },
            }
            resp = httpx.post(self.webhook_url, json=payload, timeout=10)
            logger.info("企业微信通知发送: status=%s", resp.status_code)
            return resp.status_code == 200
        except Exception as e:
            logger.warning("企业微信通知发送失败: %s", e)
            return False


def create_channels() -> list[NotificationChannel]:
    """根据配置创建通知渠道列表"""
    channels: list[NotificationChannel] = [DatabaseChannel()]

    if settings.feishu_webhook_url:
        channels.append(FeishuWebhookChannel(settings.feishu_webhook_url))
        logger.info("飞书通知渠道已启用")

    if settings.dingtalk_webhook_url:
        channels.append(DingTalkWebhookChannel(settings.dingtalk_webhook_url))
        logger.info("钉钉通知渠道已启用")

    if settings.wechat_webhook_url:
        channels.append(WeChatWorkWebhookChannel(settings.wechat_webhook_url))
        logger.info("企业微信通知渠道已启用")

    return channels