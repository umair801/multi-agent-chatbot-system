import os
import logging
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def load_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyMuPDF.
    Returns concatenated text of all pages.
    """
    try:
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        logger.info(f"PDF loaded: {file_path} ({len(text)} chars)")
        return text.strip()
    except Exception as e:
        logger.error(f"PDF load error: {e}")
        raise


def load_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file using python-docx.
    Returns concatenated paragraph text.
    """
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )
        logger.info(f"DOCX loaded: {file_path} ({len(text)} chars)")
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX load error: {e}")
        raise


def load_url(url: str, timeout: int = 10) -> str:
    """
    Fetch and extract readable text from a URL using BeautifulSoup.
    Strips scripts, styles, and nav elements.
    """
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        logger.info(f"URL loaded: {url} ({len(text)} chars)")
        return text.strip()
    except Exception as e:
        logger.error(f"URL load error: {e}")
        raise


def load_document(source: str, source_type: str) -> dict:
    """
    Unified loader entry point.

    Args:
        source:      File path or URL string
        source_type: 'pdf' | 'docx' | 'url'

    Returns:
        dict with keys: text, source, source_type, char_count
    """
    source_type = source_type.lower().strip()

    if source_type == "pdf":
        text = load_pdf(source)
    elif source_type == "docx":
        text = load_docx(source)
    elif source_type == "url":
        text = load_url(source)
    else:
        raise ValueError(f"Unsupported source_type: '{source_type}'. Use pdf, docx, or url.")

    return {
        "text": text,
        "source": source,
        "source_type": source_type,
        "char_count": len(text),
    }