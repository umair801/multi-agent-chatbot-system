import os
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
PINECONE_BATCH_SIZE = 100


def _get_openai_client():
    """Initialize OpenAI client inside function — never at module level."""
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _get_pinecone_index():
    """
    Initialize Pinecone client and return index.
    Creates index if it does not exist.
    """
    from pinecone import Pinecone, ServerlessSpec

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "agai24-rag")
    cloud = os.getenv("PINECONE_CLOUD", "aws")
    region = os.getenv("PINECONE_REGION", "us-east-1")

    if not api_key:
        raise ValueError("PINECONE_API_KEY is not set in .env")

    pc = Pinecone(api_key=api_key)

    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        logger.info(f"Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        logger.info(f"Index created: {index_name}")
    else:
        logger.info(f"Index exists: {index_name}")

    return pc.Index(index_name)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using OpenAI.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each is a list of 1536 floats)
    """
    if not texts:
        return []

    client = _get_openai_client()

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        logger.info(f"Embedded {len(texts)} texts")
        return embeddings
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise


def upsert_chunks(chunks: List[dict]) -> dict:
    """
    Embed chunks and upsert into Pinecone vector store.

    Args:
        chunks: List of chunk dicts from chunker.py
                Each must have: text, source, source_type, chunk_index

    Returns:
        dict with keys: upserted_count, status
    """
    if not chunks:
        return {"upserted_count": 0, "status": "empty"}

    index = _get_pinecone_index()

    total_upserted = 0

    # Process in batches to avoid API limits
    for i in range(0, len(chunks), PINECONE_BATCH_SIZE):
        batch = chunks[i: i + PINECONE_BATCH_SIZE]
        texts = [c["text"] for c in batch]

        embeddings = embed_texts(texts)

        vectors = []
        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            vector_id = f"{chunk['source']}__chunk_{chunk['chunk_index']}"
            # Sanitize ID for Pinecone (no special chars)
            vector_id = vector_id.replace("/", "_").replace(":", "_").replace(".", "_")[:512]

            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "source_type": chunk["source_type"],
                    "chunk_index": chunk["chunk_index"],
                },
            })

        index.upsert(vectors=vectors)
        total_upserted += len(vectors)
        logger.info(f"Upserted batch {i // PINECONE_BATCH_SIZE + 1}: {len(vectors)} vectors")

    logger.info(f"Total upserted: {total_upserted}")
    return {"upserted_count": total_upserted, "status": "success"}


def search_chunks(query: str, top_k: int = 5, filter_source: str = None) -> List[dict]:
    """
    Search Pinecone for chunks semantically similar to query.

    Args:
        query:         Natural language query string
        top_k:         Number of results to return
        filter_source: Optional source path/URL to filter results

    Returns:
        List of result dicts with keys: text, source, source_type, score
    """
    index = _get_pinecone_index()

    query_embedding = embed_texts([query])[0]

    filter_dict = None
    if filter_source:
        filter_dict = {"source": {"$eq": filter_source}}

    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )

    results = []
    for match in response.matches:
        metadata = match.metadata or {}
        results.append({
            "text": metadata.get("text", ""),
            "source": metadata.get("source", ""),
            "source_type": metadata.get("source_type", ""),
            "chunk_index": metadata.get("chunk_index", 0),
            "score": round(match.score, 4),
        })

    logger.info(f"Search returned {len(results)} results for query: '{query[:50]}'")
    return results