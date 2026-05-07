import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Default chunking config
DEFAULT_CHUNK_SIZE = 500      # tokens per chunk
DEFAULT_CHUNK_OVERLAP = 50    # token overlap between chunks


def chunk_text(
    text: str,
    source: str,
    source_type: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[dict]:
    """
    Split text into semantic chunks with overlap using tiktoken-aware splitter.

    Args:
        text:          Raw document text
        source:        Original file path or URL (for metadata)
        source_type:   'pdf' | 'docx' | 'url'
        chunk_size:    Max tokens per chunk
        chunk_overlap: Token overlap between consecutive chunks

    Returns:
        List of chunk dicts with keys: text, source, source_type, chunk_index, char_count
    """
    if not text or not text.strip():
        logger.warning(f"Empty text for source: {source}")
        return []

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")

        def token_length(text: str) -> int:
            return len(encoding.encode(text))

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=token_length,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        raw_chunks = splitter.split_text(text)

        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text.strip(),
                    "source": source,
                    "source_type": source_type,
                    "chunk_index": i,
                    "char_count": len(chunk_text),
                })

        logger.info(
            f"Chunked '{source}': {len(chunks)} chunks "
            f"(size={chunk_size}, overlap={chunk_overlap})"
        )
        return chunks

    except Exception as e:
        logger.error(f"Chunking error for '{source}': {e}")
        raise