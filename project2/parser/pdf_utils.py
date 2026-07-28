"""PDF text extraction utilities powered by PyMuPDF (fitz).

Provides functions to open uploaded PDFs (from file paths, bytes, file-like objects,
or Django Document model instances) and extract text page by page.
"""

from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Union, Optional

import fitz  # PyMuPDF
from django.db.models import Model


def open_pdf(pdf_source: Union[str, bytes, bytearray, BinaryIO, Path, Any]) -> fitz.Document:
    """Open a PDF document from various input sources using PyMuPDF.

    Args:
        pdf_source: Can be a file path (str or Path), raw bytes/bytearray,
                    a file-like object (BytesIO or UploadedFile), or a Django Document instance.

    Returns:
        fitz.Document: Opened PyMuPDF document instance.

    Raises:
        ValueError: If pdf_source is invalid, corrupt, or unsupported.
        FileNotFoundError: If a specified file path does not exist.
    """
    if pdf_source is None:
        raise ValueError("PDF source cannot be None.")

    # 1. Handle Django Document instance
    if isinstance(pdf_source, Model) or hasattr(pdf_source, 'file'):
        if hasattr(pdf_source, 'file') and pdf_source.file:
            try:
                # Try path if available on storage
                file_path = pdf_source.file.path
                return fitz.open(file_path)
            except (AttributeError, NotImplementedError):
                # Fallback to reading file stream into bytes
                pdf_source.file.seek(0)
                stream_bytes = pdf_source.file.read()
                return fitz.open(stream=stream_bytes, filetype="pdf")
        else:
            raise ValueError("Django Document object does not contain a valid file.")

    # 2. Handle string or Path file path
    if isinstance(pdf_source, (str, Path)):
        path_obj = Path(pdf_source)
        if not path_obj.exists():
            raise FileNotFoundError(f"PDF file not found at path: {pdf_source}")
        try:
            return fitz.open(str(path_obj))
        except Exception as e:
            raise ValueError(f"Failed to open PDF file at '{pdf_source}': {e}") from e

    # 3. Handle raw bytes or bytearray
    if isinstance(pdf_source, (bytes, bytearray)):
        if not pdf_source:
            raise ValueError("PDF byte content is empty.")
        try:
            return fitz.open(stream=bytes(pdf_source), filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to parse PDF bytes: {e}") from e

    # 4. Handle file-like objects (BytesIO, UploadedFile, open file descriptors)
    if hasattr(pdf_source, 'read'):
        try:
            pos = pdf_source.tell() if hasattr(pdf_source, 'tell') else None
            if hasattr(pdf_source, 'seek'):
                pdf_source.seek(0)
            content = pdf_source.read()
            if hasattr(pdf_source, 'seek') and pos is not None:
                pdf_source.seek(pos)
            
            if not content:
                raise ValueError("PDF stream content is empty.")
            return fitz.open(stream=content, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Failed to read PDF stream: {e}") from e

    raise TypeError(f"Unsupported PDF source type: {type(pdf_source).__name__}")


def extract_text_by_page(
    pdf_source: Union[str, bytes, bytearray, BinaryIO, Path, Any],
    strip_whitespace: bool = True,
    sort_text: bool = False
) -> List[Dict[str, Any]]:
    """Extract text from a PDF document page by page.

    Args:
        pdf_source: PDF file path, bytes, file-like object, or Django Document model.
        strip_whitespace: If True, leading/trailing whitespace per page text is stripped.
        sort_text: If True, sort extracted text in reading order (top-to-bottom, left-to-right).

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing page metadata and text:
            [
                {
                    "page_number": 1,
                    "text": "Page 1 text...",
                    "char_count": 142,
                    "word_count": 25
                },
                ...
            ]
    """
    doc = open_pdf(pdf_source)
    pages_data: List[Dict[str, Any]] = []

    try:
        total_pages = doc.page_count
        for i in range(total_pages):
            page = doc.load_page(i)
            # Extract text (using sort option if requested)
            text = page.get_text("text", sort=sort_text)
            if strip_whitespace:
                text = text.strip()

            pages_data.append({
                "page_number": i + 1,
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
            })
    finally:
        doc.close()

    return pages_data


def extract_page_text_list(
    pdf_source: Union[str, bytes, bytearray, BinaryIO, Path, Any],
    strip_whitespace: bool = True
) -> List[str]:
    """Extract page text as a list of strings (one string per page).

    Args:
        pdf_source: PDF file path, bytes, file-like object, or Django Document.
        strip_whitespace: If True, strips whitespace from each page's text.

    Returns:
        List[str]: List of text strings corresponding to each page.
    """
    pages = extract_text_by_page(pdf_source, strip_whitespace=strip_whitespace)
    return [p["text"] for p in pages]


def extract_full_text(
    pdf_source: Union[str, bytes, bytearray, BinaryIO, Path, Any],
    page_separator: str = "\n\n"
) -> str:
    """Extract all text from a PDF into a single concatenated string.

    Args:
        pdf_source: PDF file path, bytes, file-like object, or Django Document.
        page_separator: String used to join text from consecutive pages.

    Returns:
        str: Concatenated text content of all pages.
    """
    page_texts = extract_page_text_list(pdf_source, strip_whitespace=True)
    return page_separator.join(filter(None, page_texts))
