"""文档加载器

支持从 Markdown、TXT 格式加载运维文档内容。
"""

import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class Document:
    """文档对象"""
    def __init__(self, content: str, metadata: Optional[dict] = None):
        self.content = content
        self.metadata = metadata or {}


def load_text(content: str, source: str = "text") -> Document:
    """从纯文本创建文档

    Args:
        content: 文本内容
        source: 来源标识

    Returns:
        Document 对象
    """
    return Document(content=content, metadata={"source": source})


def load_file(file_path: str) -> Optional[Document]:
    """从文件加载文档

    支持格式: .md, .txt

    Args:
        file_path: 文件路径

    Returns:
        Document 对象，失败返回 None
    """
    if not os.path.exists(file_path):
        logger.warning("文件不存在: %s", file_path)
        return None

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".md", ".txt"):
        logger.warning("不支持的文件格式: %s", ext)
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        doc = Document(
            content=content,
            metadata={
                "source": file_path,
                "filename": os.path.basename(file_path),
                "filetype": ext[1:],
            },
        )
        logger.info("加载文档: %s (%d chars)", file_path, len(content))
        return doc
    except Exception as e:
        logger.error("加载文档失败 %s: %s", file_path, e)
        return None