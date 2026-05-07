import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.3
DEFAULT_TOP_K = 5


def _get_openai_client():
    """Initialize OpenAI client inside function — never at module level."""
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _rerank(results: list, top_k: int) -> list:
    """
    Rerank retrieved chunks by cosine similarity score descending.
    Filters out results below SIMILARITY_THRESHOLD.
    """
    filtered = [r for r in results if r.get("score", 0) >= SIMILARITY_THRESHOLD]
    reranked = sorted(filtered, key=lambda x: x.get("score", 0), reverse=True)
    return reranked[:top_k]


def _build_context(chunks: list) -> str:
    """
    Format retrieved chunks into a numbered context block for the LLM.
    Each chunk includes its source and relevance score.
    """
    if not chunks:
        return ""

    lines = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")
        lines.append(
            f"[{i}] Source: {source} (relevance: {score:.2f})\n{text}"
        )
    return "\n\n".join(lines)


def _generate_cited_answer(query: str, context: str, chunks: list) -> str:
    """
    Generate a source-cited answer using GPT-4o with retrieved context.
    """
    client = _get_openai_client()

    system_prompt = """You are a precise knowledge base assistant.
Answer the user's question using ONLY the provided context.
After your answer, list the sources you used in this format:
Sources: [1] <source_name>, [2] <source_name>
If the context does not contain enough information, say so clearly."""

    user_prompt = f"""Context:
{context}

Question: {query}

Provide a clear, accurate answer with source citations."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return f"Answer generation failed: {str(e)}"


def run_rag_query(query: str, top_k: int = DEFAULT_TOP_K) -> dict:
    """
    Full RAG query pipeline: search -> rerank -> generate cited answer.

    Args:
        query:  Natural language question
        top_k:  Number of chunks to retrieve before reranking

    Returns:
        dict with keys: query, answer, sources, chunks_used, status
    """
    logger.info(f"RAG query: '{query}'")

    try:
        from app.ingestion.embedder import search_chunks

        # Stage 1: Retrieve
        raw_results = search_chunks(query, top_k=top_k * 2)

        if not raw_results:
            return {
                "query": query,
                "answer": "No relevant documents found in the knowledge base. Please ingest documents first.",
                "sources": [],
                "chunks_used": 0,
                "status": "no_results",
            }

        # Stage 2: Rerank
        reranked = _rerank(raw_results, top_k=top_k)

        if not reranked:
            return {
                "query": query,
                "answer": "Retrieved documents did not meet the relevance threshold.",
                "sources": [],
                "chunks_used": 0,
                "status": "low_relevance",
            }

        # Stage 3: Build context
        context = _build_context(reranked)

        # Stage 4: Generate cited answer
        answer = _generate_cited_answer(query, context, reranked)

        # Extract unique sources
        sources = list({
            chunk.get("source", "unknown")
            for chunk in reranked
        })

        logger.info(f"RAG answer generated. Chunks used: {len(reranked)}, Sources: {sources}")

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "chunks_used": len(reranked),
            "status": "success",
        }

    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        return {
            "query": query,
            "answer": f"RAG pipeline error: {str(e)}",
            "sources": [],
            "chunks_used": 0,
            "status": "error",
        }


def run_rag_ingest(source: str, source_type: str) -> dict:
    """
    Ingest a document into the RAG knowledge base.

    Args:
        source:      File path or URL
        source_type: 'pdf' | 'docx' | 'url'

    Returns:
        dict with keys: source, chunk_count, upserted_count, status
    """
    logger.info(f"RAG ingest: {source_type} -> {source}")

    try:
        from app.ingestion.pipeline import run_ingestion_pipeline

        result = run_ingestion_pipeline(source, source_type)

        return {
            "source": source,
            "source_type": source_type,
            "chunk_count": result.get("chunk_count", 0),
            "upserted_count": result.get("upserted_count", 0),
            "status": result.get("status", "unknown"),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error(f"RAG ingest failed: {e}")
        return {
            "source": source,
            "source_type": source_type,
            "chunk_count": 0,
            "upserted_count": 0,
            "status": "error",
            "error": str(e),
        }