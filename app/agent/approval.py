"""Agent Auto-Repair Approval Mechanism

允许 Agent 提出修复方案，并在用户审批后自动执行修复。
审批状态通过审批令牌（token）在对话中流转。

属于 v3.0.0 Production Edition — Phase 4: Agent Auto-Repair with Approval
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Optional

logger = logging.getLogger("agent.approval")

# 内存审批存储 (token -> pending action)
_pending_approvals: dict[str, dict] = {}
_APPROVAL_TTL_SEC = 3600
_APPROVAL_MAX = 200


def _prune_approvals(now: float | None = None) -> None:
    ts = now if now is not None else time.time()
    expired = [
        token for token, pending in _pending_approvals.items()
        if ts - float(pending.get("created_at") or 0) > _APPROVAL_TTL_SEC
    ]
    for token in expired:
        _pending_approvals.pop(token, None)
    while len(_pending_approvals) > _APPROVAL_MAX:
        oldest = next(iter(_pending_approvals))
        _pending_approvals.pop(oldest, None)


def _owned_by(pending: dict, user_id: int | None) -> bool:
    owner = pending.get("user_id")
    if owner is None:
        return True
    if user_id is None:
        return False
    return int(owner) == int(user_id)


class RepairAction:
    """Agent 提出的修复动作"""

    def __init__(
        self,
        tool_name: str,
        tool_args: dict,
        description: str,
        severity: str = "info",
        requires_approval: bool = True,
    ):
        self.id = str(uuid.uuid4())[:8]
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.description = description
        self.severity = severity  # "info", "warning", "critical"
        self.requires_approval = requires_approval
        self.status = "pending"  # pending, approved, rejected, executed, failed

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool": self.tool_name,
            "args": self.tool_args,
            "description": self.description,
            "severity": self.severity,
            "requires_approval": self.requires_approval,
            "status": self.status,
        }


# ==================== 安全/危险操作分类 ====================

SAFE_OPS = {
    "docker_restart", "docker_start", "docker_stop",
    "kubectl_restart_deployment", "kubectl_scale_deployment",
    "restart_service", "retry_job",
}

DANGEROUS_OPS = {
    "docker_rm", "docker_rmi", "docker_prune",
    "kubectl_delete_pod", "kubectl_delete_deployment",
    "delete_server", "delete_database", "drop_table",
    "rm_file", "rm_rf", "shutdown", "reboot",
    "format_disk", "delete_volume",
}

AUTO_APPROVE_OPS = set()  # 未来：用户配置的自动审批白名单


def classify_tool(tool_name: str) -> str:
    """根据工具名称分类操作安全级别（优先 MCP Tool Metadata）。"""
    try:
        from app.mcp.metadata import get_tool_metadata
        meta = get_tool_metadata(tool_name)
        if meta:
            return meta.risk_level
    except Exception:
        pass
    if tool_name in DANGEROUS_OPS:
        return "dangerous"
    if tool_name in SAFE_OPS:
        return "safe"
    return "unknown"


def create_approval(action: RepairAction, user_id: int | None = None) -> str:
    """为修复动作创建审批令牌。user_id 非空时仅该用户可批准。"""
    _prune_approvals()
    token = uuid.uuid4().hex[:12]
    _pending_approvals[token] = {
        "action": action,
        "status": "pending",
        "user_id": user_id,
        "created_at": time.time(),
    }
    return token


def get_pending_approval(token: str) -> Optional[dict]:
    """根据令牌获取待审批动作"""
    _prune_approvals()
    return _pending_approvals.get(token)


def approve_action(token: str, user_id: int | None = None) -> bool:
    """批准一个待审批动作。绑定了 user_id 的令牌必须由同一用户批准。"""
    _prune_approvals()
    pending = _pending_approvals.get(token)
    if pending and pending["status"] == "pending" and _owned_by(pending, user_id):
        pending["status"] = "approved"
        _pending_approvals[token] = pending
        logger.info("Action approved: token=%s", token)
        return True
    return False


def reject_action(token: str, user_id: int | None = None) -> bool:
    """拒绝一个待审批动作。绑定了 user_id 的令牌必须由同一用户拒绝。"""
    _prune_approvals()
    pending = _pending_approvals.get(token)
    if pending and pending["status"] == "pending" and _owned_by(pending, user_id):
        pending["status"] = "rejected"
        _pending_approvals[token] = pending
        logger.info("Action rejected: token=%s", token)
        return True
    return False


def execute_approved_action(token: str, db=None) -> dict:
    """执行一个已批准的修复动作"""
    pending = _pending_approvals.get(token)
    if not pending or pending["status"] != "approved":
        return {"success": False, "error": "动作未获批准或未找到"}

    action: RepairAction = pending["action"]
    from app.tools.registry import get_tool

    tool_fn = get_tool(action.tool_name)
    if not tool_fn:
        action.status = "failed"
        return {"success": False, "error": f"工具 '{action.tool_name}' 未找到"}

    try:
        import time
        start = time.monotonic()
        raw_result = tool_fn.invoke(action.tool_args)
        duration = round((time.monotonic() - start) * 1000, 1)

        if isinstance(raw_result, (dict, list)):
            result_str = json.dumps(raw_result, ensure_ascii=False, indent=2)
        else:
            result_str = str(raw_result)

        action.status = "executed"
        _pending_approvals.pop(token, None)

        try:
            from app.monitoring.metrics import record_repair
            record_repair(success=True)
        except Exception:
            pass

        # 如果数据库可用，记录执行轨迹
        if db:
            try:
                from app.database.models import AgentTrace
                entry = AgentTrace(
                    conversation_id=0,  # 由调用方设置
                    step=99,
                    event_type="auto_repair",
                    content=f"自动修复: {action.description}",
                    tool_name=action.tool_name,
                    duration=duration,
                    meta_info={"action_id": action.id, "status": "executed"},
                )
                db.add(entry)
                db.commit()
            except Exception:
                pass

        return {
            "success": True,
            "action_id": action.id,
            "result": result_str[:500],
            "duration_ms": duration,
        }
    except Exception as e:
        action.status = "failed"
        logger.error("自动修复执行失败: %s", e)
        try:
            from app.monitoring.metrics import record_repair
            record_repair(success=False)
        except Exception:
            pass
        return {"success": False, "error": str(e)}


def format_repair_proposal(
    repair_actions: list[RepairAction],
    conversation_id: int = None,
    user_id: int | None = None,
) -> str:
    """格式化修复方案为 Markdown 输出"""
    lines = [
        "## ⚡ AI 自动修复方案",
        "",
        "| # | 操作 | 安全级别 | 需要确认 |",
        "|---|------|----------|----------|",
    ]
    for i, action in enumerate(repair_actions, 1):
        severity_icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🔔"}.get(action.severity, "ℹ️")
        approval_str = "✅ 需要确认" if action.requires_approval else "🤖 自动执行"
        lines.append(f"| {i} | {action.description} | {severity_icon} {action.severity} | {approval_str} |")

    lines.append("")
    for action in repair_actions:
        if action.requires_approval:
            token = create_approval(action, user_id=user_id)
            lines.append(f"> 在对话中输入以下内容确认执行 **{action.description}**：")
            lines.append(">")
            lines.append(f"> `确认修复 {token}`")
            lines.append("")

    lines.append("---")
    lines.append("⚠️ 危险操作均需人工确认，系统不会自动执行。")
    return "\n".join(lines)


def parse_approval_response(user_message: str, user_id: int | None = None) -> Optional[str]:
    """解析用户消息中的审批确认指令。

    只接受显式 ``确认修复 <token>``，避免一句「确认」误批他人令牌。
    """
    import re
    match = re.search(r"确认修复\s+([a-f0-9]{12})", user_message)
    if not match:
        return None
    token = match.group(1)
    pending = _pending_approvals.get(token)
    if pending is None:
        return token
    if not _owned_by(pending, user_id):
        return None
    return token
