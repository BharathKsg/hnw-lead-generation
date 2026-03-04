"""
lib/chunker.py
──────────────
Splits raw scraped text into overlapping chunks using
LangChain's MarkdownTextSplitter.
"""

from typing import List
from langchain_text_splitters import MarkdownTextSplitter
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split *text* into chunks of ~chunk_size characters with chunk_overlap
    overlap, using markdown-aware splitting (respects headers/paragraphs).

    Returns a list of non-empty string chunks.
    """
    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]
