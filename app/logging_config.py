"""生产级日志配置

统一管理 API 请求日志、Agent 执行日志、系统运行日志。
日志文件按日期轮转，保留 30 天。
v3.1.0: SecretFilter 过滤 API Key / JWT / 数据库密码。
"""

import logging
import re
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler


# 日志目录
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class SecretFilter(logging.Filter):
    """脱敏 API Key、JWT、数据库/Redis 密码，避免写入日志。"""

    _SK = re.compile(r"(sk-)([A-Za-z0-9]{4,})")
    _BEARER = re.compile(r"(Bearer\s+)([A-Za-z0-9\-._]+)", re.IGNORECASE)
    _JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
    _DB = re.compile(
        r"((?:postgres(?:ql)?|mysql|mongodb|redis)(?:\+[\w-]+)?://[^:/]+:)([^@/\s]+)(@)",
        re.IGNORECASE,
    )
    _PASSWORD_KV = re.compile(
        r"((?:password|passwd|pwd|jwt_secret|api_key|access_token)\s*[=:]\s*)([^\s,;]+)",
        re.IGNORECASE,
    )

    @staticmethod
    def mask_sk(match: re.Match) -> str:
        token = match.group(2)
        tail = token[-4:] if len(token) >= 4 else token
        return f"{match.group(1)}****{tail}"

    @classmethod
    def redact(cls, text: str) -> str:
        if not text:
            return text
        text = cls._SK.sub(cls.mask_sk, text)
        text = cls._BEARER.sub(lambda m: m.group(1) + "****", text)
        text = cls._JWT.sub("eyJ****", text)
        text = cls._DB.sub(r"\1****\3", text)
        text = cls._PASSWORD_KV.sub(r"\1****", text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = self.redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: self.redact(v) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        self.redact(a) if isinstance(a, str) else a
                        for a in record.args
                    )
        except Exception:
            pass
        return True


def _create_file_handler(filename: str, level: int, fmt: str) -> TimedRotatingFileHandler:
    """创建按天轮转的文件日志处理器"""
    handler = TimedRotatingFileHandler(
        filename=str(LOG_DIR / filename),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))
    return handler


def _create_console_handler(level: int, fmt: str) -> logging.StreamHandler:
    """创建控制台日志处理器"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))
    return handler


# 日志格式
_CONSOLE_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FILE_FMT = "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"


def setup_logging(log_level: str = "INFO") -> None:
    """配置全局日志系统"""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 移除已有处理器
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    secret_filter = SecretFilter()

    # 控制台输出
    console = _create_console_handler(level, _CONSOLE_FMT)
    console.addFilter(secret_filter)
    root_logger.addHandler(console)

    # 文件输出 — 应用日志
    app_handler = _create_file_handler("app.log", level, _FILE_FMT)
    app_handler.addFilter(secret_filter)
    root_logger.addHandler(app_handler)

    # 文件输出 — 错误日志
    err_handler = _create_file_handler("error.log", logging.ERROR, _FILE_FMT)
    err_handler.addFilter(secret_filter)
    root_logger.addHandler(err_handler)

    root_logger.addFilter(secret_filter)

    # 文件输出 — Agent 执行日志
    agent_logger = logging.getLogger("agent")
    agent_logger.setLevel(level)
    agent_logger.handlers.clear()
    agent_handler = _create_file_handler("agent.log", level, _FILE_FMT)
    agent_handler.addFilter(secret_filter)
    agent_logger.addHandler(agent_handler)
    agent_logger.addFilter(secret_filter)

    logging.info("日志系统初始化完成，日志目录: %s", LOG_DIR)
