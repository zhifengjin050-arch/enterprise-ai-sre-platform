"""文档切分器

将长文档按段落、标题、长度切分为适合 Embedding 的文本块。
"""

import re
import logging
from typing import List

from app.rag.loader import Document

logger = logging.getLogger(__name__)


class TextSplitter:
    """文本切分器

    支持按 Markdown 标题、段落、指定长度进行切分。
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split_text(self, text: str) -> List[str]:
        """将文本切分为块

        Args:
            text: 输入文本

        Returns:
            文本块列表
        """
        if not text:
            return []

        # 先按段落拆分
        paragraphs = re.split(r"\n{2,}", text)
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 < self.chunk_size or not current_chunk:
                current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # 如果某个块仍然太大，按行或按字符强制切分
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size * 1.5:
                # 按行切分
                lines = chunk.split("\n")
                sub_chunk = ""
                for line in lines:
                    expected = (sub_chunk + "\n" + line).strip() if sub_chunk else line
                    if len(expected) < self.chunk_size:
                        sub_chunk = expected
                    else:
                        if sub_chunk:
                            final_chunks.append(sub_chunk)
                        # 如果单行超过 chunk_size，强制按字符切分
                        if len(line) >= self.chunk_size:
                            for i in range(0, len(line), self.chunk_size - self.chunk_overlap):
                                segment = line[i:i + self.chunk_size]
                                if len(segment) >= self.chunk_size // 2:
                                    final_chunks.append(segment)
                            sub_chunk = ""
                        else:
                            sub_chunk = line
                if sub_chunk:
                    final_chunks.append(sub_chunk)
            else:
                final_chunks.append(chunk)

        # 如果没有段落分隔符且文本超过 chunk_size，强制按长度切分
        if len(final_chunks) == 1 and len(final_chunks[0]) > self.chunk_size * 1.5:
            text = final_chunks[0]
            final_chunks = []
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                segment = text[i:i + self.chunk_size]
                if len(segment) >= self.chunk_size // 2:
                    final_chunks.append(segment)

        logger.debug("切分结果: %d chars → %d chunks", len(text), len(final_chunks))
        return final_chunks

    def split_documents(self, documents: List[Document]) -> List[dict]:
        """将文档列表切分为带元数据的块

        Args:
            documents: 文档列表

        Returns:
            块字典列表，每个包含 content 和 metadata
        """
        chunks = []
        for doc in documents:
            text_chunks = self.split_text(doc.content)
            for i, text in enumerate(text_chunks):
                chunks.append({
                    "content": text,
                    "meta_info": {
                        **doc.metadata,
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                    },
                })
        return chunks
