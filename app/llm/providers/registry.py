"""LLM Provider Registry with fallback support"""
import logging
from typing import Optional
from app.config import settings
from app.llm.providers.base import LLMProvider, ProviderConfig
from app.llm.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger("llm.providers")


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._fallback_order: list[str] = []

    def initialize(self):
        """Initialize all configured providers"""
        providers: dict[str, LLMProvider] = {}

        # SiliconFlow
        if settings.siliconflow_api_key:
            providers["siliconflow"] = OpenAICompatibleProvider(
                ProviderConfig(
                    settings.siliconflow_api_key,
                    settings.siliconflow_base_url,
                    settings.llm_model,
                ),
                vision_model=settings.vision_model,
            )

        # OpenAI
        if settings.openai_api_key:
            providers["openai"] = OpenAICompatibleProvider(
                ProviderConfig(
                    settings.openai_api_key,
                    settings.openai_base_url or "https://api.openai.com/v1",
                    settings.openai_model,
                ),
            )

        # DeepSeek (backward compatible)
        if settings.deepseek_api_key:
            providers["deepseek"] = OpenAICompatibleProvider(
                ProviderConfig(
                    settings.deepseek_api_key,
                    settings.deepseek_base_url,
                    settings.deepseek_model_name,
                ),
            )

        self._providers = providers

        # Build fallback order
        primary = settings.llm_provider
        fallbacks_str = settings.llm_fallback_providers

        order: list[str] = []
        if primary in providers:
            order.append(primary)
        else:
            # Auto-detect first available as primary
            if providers:
                order.append(list(providers.keys())[0])

        if fallbacks_str:
            for name in fallbacks_str.split(","):
                name = name.strip()
                if name in providers and name not in order:
                    order.append(name)

        # Add any remaining providers
        for name in providers:
            if name not in order:
                order.append(name)

        self._fallback_order = order
        logger.info(
            "Provider registry initialized: primary=%s, fallbacks=%s",
            order[0] if order else "none",
            order[1:],
        )

    def get_provider(self) -> Optional[LLMProvider]:
        """Get the primary (best available) provider"""
        if not self._fallback_order:
            return None
        name = self._fallback_order[0]
        return self._providers.get(name)

    def get_all_providers(self) -> list[LLMProvider]:
        """Get all providers in fallback order"""
        return [
            self._providers[name]
            for name in self._fallback_order
            if name in self._providers
        ]

    def get_provider_with_fallback(self) -> LLMProvider:
        """Get provider, with fallback if primary fails (lazy - returns first configured)"""
        # Try each provider in order, return first that has API key
        for name in self._fallback_order:
            p = self._providers.get(name)
            if p and p.is_configured:
                return p
        # Fall back to first configured
        for p in self._providers.values():
            if p.is_configured:
                return p
        raise RuntimeError(
            "No LLM provider configured. Set SILICONFLOW_API_KEY or another provider key."
        )

    def get_vision_provider(self) -> Optional[LLMProvider]:
        """Get provider that supports vision (siliconflow typically)"""
        for name in ["siliconflow", "openai"]:
            p = self._providers.get(name)
            if p and p.is_configured:
                return p
        try:
            return self.get_provider_with_fallback()
        except RuntimeError:
            return None

    @property
    def provider_names(self) -> list[str]:
        return list(self._providers.keys())


provider_registry = ProviderRegistry()
