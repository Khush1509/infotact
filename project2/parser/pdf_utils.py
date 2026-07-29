import re
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Union, Optional

import fitz  # PyMuPDF
from django.db.models import Model


BULLET_CHARS = r'[\-\*\•\▪\⁃\–\—\◦\‣\⁃\▪\▫\^\#\>\ufffd\u2022\u2023\u25e6\u2043\u2219\u25aa\u25ab\u25cf\u25cb\u25a0\u25a1\u2013\u2014\xb7]'
BULLET_PREFIX_PATTERN = re.compile(
    r'^\s*(?:' + BULLET_CHARS + r'|\([0-9a-zA-ZivxXlcmIVXLCDM]+\)|[0-9a-zA-ZivxXlcmIVXLCDM]+[\.\)]|\d+(?:\.\d+)+)\s+'
)
HEADER_PATTERN = re.compile(
    r'^\s*(?:SECTION|ARTICLE|CLAUSE|PART|SCHEDULE|EXHIBIT)\b',
    re.IGNORECASE
)


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


def _is_header_span(span: Dict[str, Any], avg_font_size: float) -> bool:
    size = span.get("size", 0.0)
    flags = span.get("flags", 0)
    font_name = str(span.get("font", "")).lower()
    
    is_large = size >= (avg_font_size * 1.15) if avg_font_size > 0 else False
    is_bold = bool(flags & (1 << 4)) or ("bold" in font_name) or ("heavy" in font_name) or ("black" in font_name)
    return is_large or is_bold


def extract_structured_page_data(page: fitz.Page, sort_text: bool = False) -> Dict[str, Any]:
    """Extract page content logically interpreting headers, bullet points, and continuous paragraphs.

    Args:
        page: PyMuPDF Page object.
        sort_text: Whether to process blocks in reading order.

    Returns:
        Dict[str, Any]: Containing text, headers, bullet_points, paragraphs, and structured_blocks.
    """
    page_dict = page.get_text("dict", sort=sort_text)
    blocks = page_dict.get("blocks", [])

    font_sizes: List[float] = []
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if text:
                    font_sizes.append(span.get("size", 0.0))

    avg_font_size = (sum(font_sizes) / len(font_sizes)) if font_sizes else 10.0

    structured_blocks: List[Dict[str, Any]] = []
    current_block: Optional[Dict[str, Any]] = None

    def finalize_current():
        nonlocal current_block
        if current_block:
            current_block["text"] = current_block["text"].strip()
            if current_block["text"]:
                structured_blocks.append(current_block)
            current_block = None

    for block in blocks:
        if block.get("type") != 0:
            continue

        lines = block.get("lines", [])
        for line in lines:
            spans = line.get("spans", [])
            if not spans:
                continue

            line_text = "".join(s.get("text", "") for s in spans).strip()
            if not line_text:
                continue

            max_span_size = max((s.get("size", 0.0) for s in spans), default=0.0)
            is_large_line = max_span_size >= (avg_font_size * 1.18) if avg_font_size > 0 else False
            is_bold_line = any(_is_header_span(s, avg_font_size) for s in spans)
            is_short_line = len(line_text) < 80

            is_header = (
                is_large_line or
                bool(HEADER_PATTERN.match(line_text)) or
                (is_bold_line and is_short_line and not BULLET_PREFIX_PATTERN.match(line_text) and not line_text.endswith('.'))
            )

            is_bullet = bool(BULLET_PREFIX_PATTERN.match(line_text)) and not is_header

            # Normalize weird bullet symbol codepoints if needed
            if is_bullet:
                first_char = line_text[0]
                if first_char in ('·', '•', '\ufffd', '▪', '⁃', '–', '—', '◦', '‣'):
                    line_text = '• ' + line_text[1:].lstrip()

            if is_header:
                finalize_current()
                structured_blocks.append({
                    "type": "header",
                    "text": line_text
                })
            elif is_bullet:
                finalize_current()
                current_block = {
                    "type": "bullet_point",
                    "text": line_text
                }
            else:
                if current_block is None:
                    current_block = {
                        "type": "paragraph",
                        "text": line_text
                    }
                else:
                    prev_text = current_block["text"]
                    if prev_text.endswith("-") and len(prev_text) > 1 and prev_text[-2].isalpha():
                        current_block["text"] = prev_text[:-1] + line_text
                    else:
                        current_block["text"] = prev_text + " " + line_text

        finalize_current()

    headers = [b["text"] for b in structured_blocks if b["type"] == "header"]
    bullet_points = [b["text"] for b in structured_blocks if b["type"] == "bullet_point"]
    paragraphs = [b["text"] for b in structured_blocks if b["type"] == "paragraph"]

    text_chunks: List[str] = []
    curr_group: List[str] = []

    for b in structured_blocks:
        b_type = b["type"]
        b_text = b["text"]

        if b_type == "bullet_point":
            curr_group.append(b_text)
        else:
            if curr_group:
                text_chunks.append("\n".join(curr_group))
                curr_group = []
            text_chunks.append(b_text)
    if curr_group:
        text_chunks.append("\n".join(curr_group))

    full_text = "\n\n".join(text_chunks)

    return {
        "text": full_text,
        "headers": headers,
        "bullet_points": bullet_points,
        "paragraphs": paragraphs,
        "structured_blocks": structured_blocks,
    }


def extract_text_by_page(
    pdf_source: Union[str, bytes, bytearray, BinaryIO, Path, Any],
    strip_whitespace: bool = True,
    sort_text: bool = False,
    preserve_structure: bool = True
) -> List[Dict[str, Any]]:
    """Extract text from a PDF document page by page with optional structure preservation.

    Args:
        pdf_source: PDF file path, bytes, file-like object, or Django Document model.
        strip_whitespace: If True, leading/trailing whitespace per page text is stripped.
        sort_text: If True, sort extracted text in reading order (top-to-bottom, left-to-right).
        preserve_structure: If True, logically interprets headers, bullet points, and continuous paragraphs.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing page metadata and text:
            [
                {
                    "page_number": 1,
                    "text": "Page 1 text...",
                    "char_count": 142,
                    "word_count": 25,
                    "paragraphs": [...],
                    "headers": [...],
                    "bullet_points": [...],
                    "structured_blocks": [...]
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
            headers: List[str] = []
            bullet_points: List[str] = []
            paragraphs: List[str] = []
            structured_blocks: List[Dict[str, Any]] = []

            if preserve_structure:
                try:
                    struct_data = extract_structured_page_data(page, sort_text=sort_text)
                    text = struct_data["text"]
                    headers = struct_data["headers"]
                    bullet_points = struct_data["bullet_points"]
                    paragraphs = struct_data["paragraphs"]
                    structured_blocks = struct_data["structured_blocks"]
                except Exception:
                    # Fallback to plain text extraction on structure parsing issue
                    text = page.get_text("text", sort=sort_text)
            else:
                text = page.get_text("text", sort=sort_text)

            if strip_whitespace:
                text = text.strip()

            pages_data.append({
                "page_number": i + 1,
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
                "paragraphs": paragraphs,
                "headers": headers,
                "bullet_points": bullet_points,
                "structured_blocks": structured_blocks,
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

