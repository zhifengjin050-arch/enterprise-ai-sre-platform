from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "3.3.0"
JWT_INSECURE_PRODUCTION_MSG = "JWT_SECRET is insecure for production environment"


class Settings(BaseSettings):
    """应用配置，从环境变量读取"""

    # ========== LLM Provider Layer (v3.0.0) ==========
    # Primary provider: siliconflow | openai | deepseek | azure
    llm_provider: str = "siliconflow"

    # Provider-specific configs (each provider's API key, base url, model)
    # SiliconFlow (default)
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    llm_model: str = "deepseek-ai/DeepSeek-V4-Flash"
    # 视觉模型 (图片理解)
    vision_model: str = "Qwen/Qwen3-VL-8B-Instruct"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o"

    # DeepSeek (backward compatible)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model_name: str = "deepseek-chat"

    # Azure OpenAI
    azure_api_key: str = ""
    azure_base_url: str = ""
    azure_model: str = "gpt-4o"
    azure_api_version: str = "2024-02-15-preview"

    # Fallback providers (comma-separated, tried in order when primary fails)
    llm_fallback_providers: str = ""

    @property
    def effective_llm_api_key(self) -> str:
        """获取有效的 LLM API Key (新配置优先)"""
        return self.siliconflow_api_key or self.deepseek_api_key

    @property
    def effective_llm_base_url(self) -> str:
        """获取有效的 LLM Base URL (新配置优先)"""
        return self.siliconflow_base_url or self.deepseek_base_url

    @property
    def effective_llm_model(self) -> str:
        """获取有效的 LLM 模型名 (新配置优先)"""
        return self.llm_model or self.deepseek_model_name

    # 应用
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # 环境
    environment: str = "development"

    # Demo 模式（无需真实服务器即可体验）
    demo_mode: bool = False

    # 安全
    jwt_secret: str = "change-me-to-a-random-secret"
    jwt_expire_minutes: int = 1440  # 24 小时
    cors_origins: str = "http://localhost:80,http://localhost:8000,http://localhost:5173"
    rate_limit_per_minute: int = 60
    allow_register: bool = True
    metrics_token: str = ""

    def is_production(self) -> bool:
        return (self.environment or "").strip().lower() in ("production", "prod")

    def validate_production_security(self) -> None:
        """生产环境启动门禁。开发环境不拦截，保持兼容。"""
        if not self.is_production():
            return

        jwt = (self.jwt_secret or "").strip()
        lowered = jwt.lower()
        forbidden = ("change-me", "secret", "password", "test")
        insecure = (
            (not jwt)
            or (len(jwt) < 32)
            or any(frag in lowered for frag in forbidden)
        )
        if insecure:
            raise RuntimeError(JWT_INSECURE_PRODUCTION_MSG)

    # 数据库
    database_url: str = "sqlite:///./devops.db"

    # Redis 缓存与任务队列
    redis_url: str = "redis://localhost:6379/0"

    # SSH
    ssh_timeout: int = 10
    ssh_command_timeout: int = 30

    # Kubernetes
    kubernetes_enabled: bool = False
    kubeconfig_path: str = ""
    kubernetes_timeout: int = 10
    kubernetes_allow_restart: bool = False

    # 监控与告警
    metrics_collect_interval: int = 15  # 指标采集间隔（秒）
    alert_evaluate_interval: int = 30  # 告警评估间隔（秒）

    # 通知渠道 Webhook
    feishu_webhook_url: str = ""
    dingtalk_webhook_url: str = ""
    wechat_webhook_url: str = ""

    # Embedding / RAG
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 128

    # Prometheus
    prometheus_push_gateway: str = ""

    # MCP（stdio Client → 项目2 Enterprise DevOps MCP Server）
    enable_mcp: bool = False
    mcp_server_command: str = "python"
    # 逗号分隔，例如: -m,app.server
    mcp_server_args: str = "-m,app.server"
    mcp_server_cwd: str = ""
    mcp_timeout: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
