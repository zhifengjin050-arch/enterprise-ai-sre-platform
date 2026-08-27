"""LLM Client v3 — Multi-Provider Client with Auto-Fallback

基于 Provider Registry 实现多 LLM 供应商支持：
- SiliconFlow (默认)
- OpenAI
- DeepSeek
- Azure OpenAI (通过 Provider 扩展)
- 自动降级与回退
"""

from __future__ import annotations

from openai.types.chat import ChatCompletionMessage

from app.llm.providers.registry import provider_registry


class LLMClient:
    """多供应商 LLM 客户端（自动回退）"""

    def __init__(self):
        # Initialize providers if not already done
        if not provider_registry.provider_names:
            provider_registry.initialize()

    # ==================== 文本推理 ====================

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """基础聊天调用（文本模型）"""
        provider = provider_registry.get_provider_with_fallback()
        return provider.chat(messages, temperature=temperature, max_tokens=max_tokens)

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatCompletionMessage:
        """支持 Function Calling 的聊天调用（文本模型）"""
        provider = provider_registry.get_provider_with_fallback()
        return provider.chat_with_tools(messages, tools, temperature=temperature, max_tokens=max_tokens)

    # ==================== 视觉理解 ====================

    def chat_with_vision(
        self,
        text_prompt: str,
        image_url: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """视觉理解调用（图片分析）"""
        provider = provider_registry.get_vision_provider()
        return provider.chat_with_vision(text_prompt, image_url, temperature=temperature, max_tokens=max_tokens)

    def analyze_ops_screenshot(
        self,
        image_url: str,
        context: str = "服务器监控/Grafana 面板",
    ) -> str:
        """运维截图分析（快捷方法）"""
        prompt = (
            f"你是一个资深 DevOps/SRE 工程师。请分析以下运维截图（来源：{context}）：\n\n"
            "请关注：\n"
            "1. 是否有异常指标（红色告警、突增突降、超阈值）\n"
            "2. 资源使用趋势（CPU、内存、磁盘、网络）\n"
            "3. 服务状态（Running/CrashLoopBackOff/OOMKilled）\n"
            "4. 日志中的错误模式（Exception、Error、Timeout）\n"
            "5. 需要立即关注的问题\n\n"
            "请以结构化格式输出分析结果。"
        )
        return self.chat_with_vision(prompt, image_url)

    # ==================== 通用 ====================

    @property
    def is_configured(self) -> bool:
        """检查是否有任一供应商已配置"""
        try:
            p = provider_registry.get_provider_with_fallback()
            return p is not None
        except RuntimeError:
            return False

    @property
    def current_provider(self) -> str:
        """获取当前生效的供应商名称"""
        try:
            p = provider_registry.get_provider_with_fallback()
            return p.name if p else "none"
        except RuntimeError:
            return "none"

    @property
    def model(self) -> str:
        """当前生效的文本模型名（兼容旧 DeepSeekClient.model）"""
        from app.config import settings
        try:
            p = provider_registry.get_provider_with_fallback()
            return getattr(p, "name", None) or settings.effective_llm_model
        except RuntimeError:
            return settings.effective_llm_model


# 向后兼容：DeepSeekClient 别名指向 LLMClient
DeepSeekClient = LLMClient
