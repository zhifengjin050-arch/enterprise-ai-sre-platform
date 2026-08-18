"""OpenAI-compatible LLM provider"""
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from app.llm.providers.base import LLMProvider, ProviderConfig


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, vision_model: str = ""):
        self._config = config
        self._vision_model = vision_model or config.model
        self._client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatCompletionMessage:
        kwargs = dict(
            model=self._config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message

    def chat_with_vision(
        self,
        text_prompt: str,
        image_url: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ]
        resp = self._client.chat.completions.create(
            model=self._vision_model,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    @property
    def is_configured(self) -> bool:
        return bool(self._config.api_key)

    @property
    def name(self) -> str:
        return self._config.model

    @property
    def client(self) -> OpenAI:
        return self._client