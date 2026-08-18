"""Abstract LLM Provider"""
from abc import ABC, abstractmethod
from typing import Optional
from openai.types.chat import ChatCompletionMessage


class ProviderConfig:
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        pass

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatCompletionMessage:
        pass

    @abstractmethod
    def chat_with_vision(
        self,
        text_prompt: str,
        image_url: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass