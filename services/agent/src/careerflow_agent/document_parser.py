from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader

from .contracts import SourceSpan

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
type ResumeMediaType = Literal[
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
SUPPORTED_RESUME_MEDIA_TYPES = frozenset({PDF_MEDIA_TYPE, DOCX_MEDIA_TYPE})
MAX_RESUME_BYTES = 10 * 1024 * 1024
MAX_EVIDENCE_ITEMS = 500
MAX_PDF_PAGES = 100
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_ARCHIVE_ENTRIES = 2_000


class ResumeParseError(ValueError):
    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


@dataclass(frozen=True)
class ParsedStatement:
    statement: str
    source_span: SourceSpan


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _append_statement(
    statements: list[ParsedStatement],
    value: str,
    *,
    cursor: int,
    page: int | None = None,
    section: str | None = None,
) -> int:
    normalized = _normalize(value)
    if not normalized or len(statements) >= MAX_EVIDENCE_ITEMS:
        return cursor
    end = cursor + len(normalized)
    statements.append(
        ParsedStatement(
            statement=normalized,
            source_span=SourceSpan(page=page, section=section, start=cursor, end=end),
        )
    )
    return end + 1


def _parse_pdf(content: bytes) -> list[ParsedStatement]:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise ResumeParseError("password_protected")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ResumeParseError("document_too_complex")
        statements: list[ParsedStatement] = []
        cursor = 0
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for line in text.splitlines():
                cursor = _append_statement(
                    statements,
                    line,
                    cursor=cursor,
                    page=page_number,
                    section=f"page:{page_number}",
                )
        return statements
    except ResumeParseError:
        raise
    except Exception as error:
        raise ResumeParseError("invalid_pdf") from error


def _iter_docx_blocks(document: DocumentType) -> list[Paragraph | Table]:
    return list(document.iter_inner_content())


def _parse_docx(content: bytes) -> list[ParsedStatement]:
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > MAX_DOCX_ARCHIVE_ENTRIES
                or sum(entry.file_size for entry in entries) > MAX_DOCX_UNCOMPRESSED_BYTES
            ):
                raise ResumeParseError("document_too_complex")
        document = Document(BytesIO(content))
        statements: list[ParsedStatement] = []
        cursor = 0
        section = "document"
        paragraph_number = 0
        table_number = 0
        for block in _iter_docx_blocks(document):
            if len(statements) >= MAX_EVIDENCE_ITEMS:
                break
            if isinstance(block, Paragraph):
                paragraph_number += 1
                normalized = _normalize(block.text)
                if block.style and block.style.name.lower().startswith("heading") and normalized:
                    section = normalized
                cursor = _append_statement(
                    statements,
                    normalized,
                    cursor=cursor,
                    section=f"{section} · paragraph:{paragraph_number}",
                )
                continue

            table_number += 1
            for row_number, row in enumerate(block.rows, start=1):
                if len(statements) >= MAX_EVIDENCE_ITEMS:
                    break
                cells = [_normalize(cell.text) for cell in row.cells]
                cursor = _append_statement(
                    statements,
                    " | ".join(dict.fromkeys(cell for cell in cells if cell)),
                    cursor=cursor,
                    section=f"{section} · table:{table_number} · row:{row_number}",
                )
        return statements
    except ResumeParseError:
        raise
    except Exception as error:
        raise ResumeParseError("invalid_docx") from error


def parse_resume(content: bytes, media_type: ResumeMediaType) -> list[ParsedStatement]:
    if media_type == PDF_MEDIA_TYPE:
        return _parse_pdf(content)
    if media_type == DOCX_MEDIA_TYPE:
        return _parse_docx(content)
    raise ResumeParseError("unsupported_media_type")
