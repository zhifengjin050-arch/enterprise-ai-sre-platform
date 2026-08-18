"""Embedding 服务（可配置多种模型后端）

支持通过 OpenAI 兼容接口获取文本向量化表示。
当前默认使用与 LLM 相同的 API 端点（如 SiliconFlow），
支持 text-embedding-ada-002 等模型。
"""

import json
import logging
import hashlib
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding 向量化服务"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.effective_llm_api_key
        self.base_url = base_url or settings.effective_llm_base_url
        self.model = model or settings.embedding_model

        # 缓存
        self._cache: dict[str, List[float]] = {}

    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get_embedding(self, text: str, allow_fallback: bool = True) -> List[float]:
        """获取单段文本的向量表示。Hub 文档应关闭降级以免污染相似度。"""
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            embedding = self._call_embedding_api(text)
            self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            if not allow_fallback:
                logger.warning("Embedding API 调用失败且禁止降级: %s", e)
                raise
            logger.warning("Embedding API 调用失败: %s，使用降级方案", e)
            return self._fallback_embedding(text)

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量表示

        Args:
            texts: 文本列表

        Returns:
            向量数组列表
        """
        return [self.get_embedding(t) for t in texts]

    def _call_embedding_api(self, text: str) -> List[float]:
        """调用 Embedding API

        使用 OpenAI 兼容接口格式。
        """
        url = f"{self.base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
        }

        response = httpx.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        return data["data"][0]["embedding"]

    def _fallback_embedding(self, text: str) -> List[float]:
        """降级方案：使用简单哈希生成固定维度向量

        当 Embedding API 不可用时使用，确保系统不中断。
        """
        import hashlib
        dimension = 128
        vec = []
        for i in range(dimension):
            h = hashlib.md5(f"{text}{i}".encode()).hexdigest()
            val = int(h[:8], 16) / 0xFFFFFFFF
            vec.append(val)
        return vec

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        return 128  # 降级方案维度，实际 API 返回通常是 1536


# 全局单例
embedding_service = EmbeddingService()