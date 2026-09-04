from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PageObject, PdfReader

from .contracts import ResumeFieldSuggestion, ResumeSuggestionPath, SourceSpan

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
MAX_PDF_LINK_ANNOTATIONS = 1_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_ARCHIVE_ENTRIES = 2_000

EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
)
LINK_PATTERN = re.compile(
    r"(?:(?:https?://)?(?:www\.)?(?:linkedin\.com/in|github\.com)/[^\s|,;]+)",
    re.IGNORECASE,
)
SCHOOL_PATTERN = re.compile(
    r"\b(?:university|college|institute(?: of technology)?|polytechnic|academy)\b",
    re.IGNORECASE,
)
DEGREE_PATTERN = re.compile(
    r"\b(?P<degree>"
    r"Bachelor(?:'s)?(?: of (?:Science|Arts|Engineering))?"
    r"|Master(?:'s)?(?: of (?:Science|Arts|Engineering|Business Administration))?"
    r"|Doctor(?:ate)?(?: of Philosophy)?|Associate(?:'s)?(?: of (?:Science|Arts))?"
    r"|B\.?\s?S\.?|B\.?\s?A\.?|M\.?\s?S\.?|M\.?\s?A\.?|Ph\.?\s?D\.?)"
    r"(?:\s+in\s+(?P<field>[A-Za-z][A-Za-z &/+-]*?))?"
    r"(?=\s*(?:[|,;•]|(?:Expected\s+)?(?:May|June|August|December)?\s*20\d{2}|$))",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b(?:19[5-9]\d|20\d{2}|2100)\b")
SECTION_HEADINGS = {
    "education",
    "experience",
    "work experience",
    "projects",
    "skills",
    "technical skills",
    "summary",
    "objective",
    "contact",
}


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


def _profile_link(value: str, *, require_scheme: bool) -> tuple[ResumeSuggestionPath, str] | None:
    cleaned = value.strip().rstrip(".)]")
    if not cleaned:
        return None
    if not cleaned.lower().startswith(("http://", "https://")):
        if require_scheme:
            return None
        cleaned = f"https://{cleaned}"

    try:
        parsed = urlsplit(cleaned)
        if parsed.scheme.casefold() not in {"http", "https"} or parsed.username or parsed.password:
            return None
        if parsed.port not in {None, 80, 443}:
            return None
    except ValueError:
        return None

    host = (parsed.hostname or "").casefold()
    segments = [segment for segment in parsed.path.split("/") if segment]
    if host in {"linkedin.com", "www.linkedin.com"}:
        if len(segments) != 2 or segments[0].casefold() != "in":
            return None
        path: ResumeSuggestionPath = "links.linkedin"
    elif host in {"github.com", "www.github.com"}:
        # The profile field must not accidentally capture a project repository URL.
        if len(segments) != 1:
            return None
        path = "links.github"
    else:
        return None

    normalized_path = f"/{'/'.join(segments)}"
    normalized = urlunsplit(("https", host, normalized_path, "", ""))
    return path, normalized


def _pdf_profile_links(page: PageObject, *, annotation_budget: int) -> tuple[list[str], int]:
    annotations = page.get("/Annots") or []
    links: list[str] = []
    inspected = 0
    for annotation_reference in annotations:
        if inspected >= annotation_budget:
            break
        inspected += 1
        try:
            annotation = annotation_reference.get_object()
            if annotation.get("/Subtype") != "/Link":
                continue
            action_reference = annotation.get("/A")
            if action_reference is None:
                continue
            action = action_reference.get_object()
            if action.get("/S") != "/URI":
                continue
            link = _profile_link(str(action.get("/URI", "")), require_scheme=True)
            if link is not None:
                links.append(link[1])
        except Exception:
            # A malformed optional annotation must not make otherwise-readable text unusable.
            continue
    return list(dict.fromkeys(links)), inspected


def _parse_pdf(content: bytes) -> list[ParsedStatement]:
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise ResumeParseError("password_protected")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ResumeParseError("document_too_complex")
        statements: list[ParsedStatement] = []
        cursor = 0
        seen_profile_links: set[str] = set()
        inspected_annotations = 0
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
                for match in LINK_PATTERN.finditer(line):
                    parsed_link = _profile_link(match.group(0), require_scheme=False)
                    if parsed_link is not None:
                        seen_profile_links.add(parsed_link[1])

            annotation_budget = MAX_PDF_LINK_ANNOTATIONS - inspected_annotations
            if annotation_budget <= 0:
                continue
            links, inspected = _pdf_profile_links(page, annotation_budget=annotation_budget)
            inspected_annotations += inspected
            for link_url in links:
                if link_url in seen_profile_links:
                    continue
                cursor = _append_statement(
                    statements,
                    link_url,
                    cursor=cursor,
                    page=page_number,
                    section=f"page:{page_number} · hyperlink",
                )
                seen_profile_links.add(link_url)
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


def _name_candidate(statements: list[ParsedStatement]) -> tuple[list[str], SourceSpan] | None:
    for item in statements[:8]:
        candidate = re.split(r"\s*[|•]\s*", item.statement, maxsplit=1)[0].strip()
        lowered = candidate.casefold()
        if (
            lowered in SECTION_HEADINGS
            or "@" in candidate
            or "http" in lowered
            or any(character.isdigit() for character in candidate)
        ):
            continue
        tokens = candidate.split()
        if not 2 <= len(tokens) <= 4:
            continue
        if any(token.casefold() in {"of", "and", "engineer", "developer"} for token in tokens):
            continue
        if all(re.fullmatch(r"[A-Za-z][A-Za-z'.-]*", token) for token in tokens):
            return tokens, item.source_span
    return None


def extract_profile_suggestions(
    statements: list[ParsedStatement],
) -> list[ResumeFieldSuggestion]:
    """Extract conservative profile suggestions without a model or network request."""
    suggestions: list[ResumeFieldSuggestion] = []
    seen: set[str] = set()

    def add(
        path: ResumeSuggestionPath, value: str, confidence: float, source_span: SourceSpan
    ) -> None:
        if path in seen or not value.strip():
            return
        suggestions.append(
            ResumeFieldSuggestion(
                canonical_path=path,
                value=value.strip(),
                confidence=confidence,
                source_span=source_span,
            )
        )
        seen.add(path)

    name = _name_candidate(statements)
    if name:
        tokens, source_span = name
        add("identity.first_name", tokens[0], 0.8, source_span)
        add("identity.last_name", tokens[-1], 0.8, source_span)

    education_indexes: set[int] = set()
    for index, item in enumerate(statements):
        statement = item.statement
        email = EMAIL_PATTERN.search(statement)
        if email:
            add("contact.email", email.group(0), 1.0, item.source_span)
        phone = PHONE_PATTERN.search(statement)
        if phone:
            add("contact.phone", phone.group(0), 0.98, item.source_span)
        for link in LINK_PATTERN.finditer(statement):
            profile_link = _profile_link(link.group(0), require_scheme=False)
            if profile_link is not None:
                path, value = profile_link
                add(path, value, 1.0, item.source_span)

        if SCHOOL_PATTERN.search(statement):
            education_indexes.add(index)
            school = re.split(r"\s*[|•]\s*", statement, maxsplit=1)[0].strip()
            add("education.0.school", school, 0.85, item.source_span)

        degree = DEGREE_PATTERN.search(statement)
        if degree:
            education_indexes.add(index)
            add("education.0.degree", degree.group("degree"), 0.9, item.source_span)
            if degree.group("field"):
                add("education.0.field_of_study", degree.group("field"), 0.85, item.source_span)

        if item.source_span.section and "education" in item.source_span.section.casefold():
            education_indexes.add(index)

    for index in sorted(education_indexes):
        for nearby in statements[index : index + 3]:
            year = YEAR_PATTERN.search(nearby.statement)
            if year:
                add("education.0.graduation_year", year.group(0), 0.8, nearby.source_span)
                return suggestions
    return suggestions
