from __future__ import annotations

import io
import re
import unicodedata

import pdfplumber
from docx import Document

from config import MAX_EXTRACTED_CHARS, MAX_PDF_PAGES
from utils import clean_line

def extract_pdf_text(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    chunks: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        if page_count == 0:
            raise ValueError("The PDF does not contain any pages.")
        if page_count > MAX_PDF_PAGES:
            warnings.append(
                f"Only the first {MAX_PDF_PAGES} of {page_count} pages were analyzed."
            )
        for page in pdf.pages[:MAX_PDF_PAGES]:
            try:
                page_text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            except Exception:
                page_text = ""
            if page_text.strip():
                chunks.append(page_text)
    text = "\n\n".join(chunks).strip()
    if not text:
        raise ValueError(
            "No selectable text was found in this PDF. Scanned image-only PDFs are not supported; export a text-based PDF or upload a DOCX."
        )
    return text, warnings


def extract_docx_text(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    document = Document(io.BytesIO(data))
    chunks: list[str] = []
    for paragraph in document.paragraphs:
        paragraph_text = (paragraph.text or "").strip()
        if paragraph_text:
            chunks.append(paragraph_text)
    for table in document.tables:
        for row in table.rows:
            cells: list[str] = []
            previous = None
            for cell in row.cells:
                value = clean_line(cell.text)
                if value and value != previous:
                    cells.append(value)
                previous = value
            if cells:
                chunks.append(" | ".join(cells))
    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError(
            "No readable text was found in this DOCX file. Add text-based content and try again."
        )
    return text, warnings


def finalize_extracted_text(text: str, warnings: list[str]) -> tuple[str, list[str]]:
    cleaned = (text or "").replace("\x00", " ")
    cleaned = "".join(
        char
        for char in cleaned
        if char in "\n\t" or unicodedata.category(char)[0] != "C"
    )
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned).strip()
    if len(cleaned) > MAX_EXTRACTED_CHARS:
        cleaned = cleaned[:MAX_EXTRACTED_CHARS]
        warnings.append(
            f"Resume text was truncated to {MAX_EXTRACTED_CHARS:,} characters for analysis."
        )
    return cleaned, warnings


def extract_resume_text(file_name: str, data: bytes) -> tuple[str, list[str]]:
    lower_name = (file_name or "").lower()
    if lower_name.endswith(".pdf"):
        text, warnings = extract_pdf_text(data)
    elif lower_name.endswith(".docx"):
        text, warnings = extract_docx_text(data)
    else:
        raise ValueError("Unsupported file type. Upload a PDF or DOCX resume.")
    return finalize_extracted_text(text, warnings)
