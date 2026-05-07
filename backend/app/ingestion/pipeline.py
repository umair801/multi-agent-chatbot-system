import logging
from typing import List
from dotenv import load_dotenv
from app.ingestion.loaders import load_document
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import upsert_chunks

load_dotenv()
logger = logging.getLogger(__name__)


def run_ingestion_pipeline(
    source: str,
    source_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> dict:
    """
    Full ingestion pipeline: load -> chunk.
    Embedding and storage handled in Step 7.

    Args:
        source:       File path or URL
        source_type:  'pdf' | 'docx' | 'url'
        chunk_size:   Tokens per chunk
        chunk_overlap: Token overlap

    Returns:
        dict with keys: source, source_type, chunks, chunk_count, char_count, status
    """
    logger.info(f"Ingestion pipeline start: {source_type} -> {source}")

    try:
        # Stage 1: Load
        doc = load_document(source, source_type)
        text = doc["text"]

        if not text:
            return {
                "source": source,
                "source_type": source_type,
                "chunks": [],
                "chunk_count": 0,
                "char_count": 0,
                "status": "empty",
                "error": "Document loaded but contained no text",
            }

        # Stage 2: Chunk
        chunks = chunk_text(
            text=text,
            source=source,
            source_type=source_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Stage 3: Embed + store
        upsert_result = upsert_chunks(chunks)

        logger.info(f"Ingestion complete: {len(chunks)} chunks from {source}")

        return {
            "source": source,
            "source_type": source_type,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "char_count": doc["char_count"],
            "upserted_count": upsert_result.get("upserted_count", 0),
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Ingestion pipeline error: {e}")
        return {
            "source": source,
            "source_type": source_type,
            "chunks": [],
            "chunk_count": 0,
            "char_count": 0,
            "status": "error",
            "error": str(e),
        }