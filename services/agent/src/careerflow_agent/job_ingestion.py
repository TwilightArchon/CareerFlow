from __future__ import annotations

import asyncio
import hashlib
import html
import ipaddress
import json
import re
import socket
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from pydantic import AnyHttpUrl

from .contracts import (
    JobIngestionStatus,
    JobPosting,
    JobRequirement,
    Platform,
    PlatformDetection,
    SourceSpan,
)
from .database import Database

MAX_JOB_PAGE_BYTES = 2 * 1024 * 1024
MAX_JOB_DESCRIPTION_CHARS = 200_000
MAX_REQUIREMENTS = 60
MAX_REDIRECTS = 5
TRACKING_PARAMETERS = {"ref", "source", "src"}
REQUIREMENT_HEADINGS = {
    "requirements",
    "qualifications",
    "minimum qualifications",
    "basic qualifications",
    "required qualifications",
    "your background",
    "what you bring",
    "what you'll bring",
    "what you will bring",
}
STOP_HEADINGS = {
    "benefits",
    "compensation",
    "equal opportunity employer",
    "equal employment opportunity",
    "about us",
    "about the company",
    "accessibility",
    "privacy",
}
REQUIREMENT_SIGNAL = re.compile(
    r"\b(?:required|must|minimum|experience|degree|proficien|knowledge|ability|familiar|skill)\w*\b",
    re.IGNORECASE,
)
FLAT_REQUIREMENT_START = re.compile(
    r"(?=\b(?:Candidates? must|Ability to|Good conceptual|Effective working|Self[- ]motivated|"
    r"Obtaining|Currently (?:pursuing|enrolled)|Bachelor(?:'s)?|Master(?:'s)?)\b)",
    re.IGNORECASE,
)

type HostResolver = Callable[[str], Awaitable[list[str]]]


class JobIngestionError(ValueError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _FetchedPage:
    status_code: int
    headers: httpx.Headers
    url: str
    text: str

    @property
    def is_redirect(self) -> bool:
        return self.status_code in {301, 302, 303, 307, 308}


class _JobHtmlParser(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical_url: str | None = None
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self.json_ld_blocks: list[str] = []
        self._current_json_ld: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value or "" for key, value in attrs}
        lowered = tag.casefold()
        if lowered in {"script", "style", "noscript", "svg"}:
            if (
                lowered == "script"
                and attributes.get("type", "").casefold() == "application/ld+json"
            ):
                self._in_json_ld = True
                self._current_json_ld = []
            else:
                self._ignored_depth += 1
            return
        if lowered == "title":
            self._in_title = True
        elif lowered == "meta":
            key = (attributes.get("property") or attributes.get("name") or "").casefold()
            content = attributes.get("content", "").strip()
            if key and content:
                self.meta[key] = content
        elif lowered == "link" and attributes.get("rel", "").casefold() == "canonical":
            self.canonical_url = attributes.get("href") or None
        if lowered in self.BLOCK_TAGS:
            self.body_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld_blocks.append("".join(self._current_json_ld))
            self._current_json_ld = []
            return
        if lowered in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if lowered == "title":
            self._in_title = False
        if lowered in self.BLOCK_TAGS:
            self.body_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._current_json_ld.append(data)
        elif self._ignored_depth == 0:
            if self._in_title:
                self.title_parts.append(data)
            self.body_parts.append(data)


def _clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in html.unescape(value).splitlines()]
    return "\n".join(line for line in lines if line)


def _html_fragment_to_text(value: str) -> str:
    parser = _JobHtmlParser()
    parser.feed(value)
    return _clean_text("".join(parser.body_parts))


def _iter_objects(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_objects(child)


def _job_posting_json_ld(parser: _JobHtmlParser) -> dict[str, Any] | None:
    for raw_block in parser.json_ld_blocks:
        raw = raw_block.strip()
        if not raw:
            continue
        try:
            payload: Any = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for candidate in _iter_objects(payload):
            raw_type = candidate.get("@type")
            types = raw_type if isinstance(raw_type, list) else [raw_type]
            if any(str(value).casefold() == "jobposting" for value in types):
                return candidate
    return None


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return _clean_text("\n".join(_string_value(item) for item in value))
    if isinstance(value, dict):
        return _clean_text(str(value.get("name") or value.get("value") or ""))
    return ""


def _organization_name(posting: dict[str, Any]) -> str:
    organization = posting.get("hiringOrganization")
    return _string_value(organization)


def _location(posting: dict[str, Any]) -> str:
    locations = posting.get("jobLocation")
    if not isinstance(locations, list):
        locations = [locations]
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if not isinstance(address, dict):
            continue
        parts = [
            _string_value(address.get("addressLocality")),
            _string_value(address.get("addressRegion")),
            _string_value(address.get("addressCountry")),
        ]
        normalized = ", ".join(dict.fromkeys(part for part in parts if part))
        if normalized:
            return normalized
    return ""


def _canonicalize_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_PARAMETERS
    ]
    return urlunsplit(
        (
            parts.scheme.casefold(),
            parts.netloc.casefold(),
            parts.path or "/",
            urlencode(filtered_query),
            "",
        )
    )


def _platform_detection(raw_url: str) -> PlatformDetection:
    hostname = urlsplit(raw_url).hostname or ""
    lowered = hostname.casefold()
    if lowered.endswith("myworkdayjobs.com") or ".workday." in lowered:
        return PlatformDetection(
            platform=Platform.WORKDAY,
            confidence=0.99,
            signals=["hostname:workday"],
        )
    if lowered.endswith("greenhouse.io") or lowered.endswith("greenhouse.com"):
        return PlatformDetection(
            platform=Platform.GREENHOUSE,
            confidence=0.99,
            signals=["hostname:greenhouse"],
        )
    if lowered.endswith("lever.co"):
        return PlatformDetection(
            platform=Platform.LEVER,
            confidence=0.99,
            signals=["hostname:lever"],
        )
    return PlatformDetection(
        platform=Platform.UNKNOWN,
        confidence=0.25,
        signals=["hostname:unrecognized"],
    )


def _requirements_from_description(description: str) -> list[JobRequirement]:
    lines = description.splitlines()
    requirements: list[JobRequirement] = []
    seen: set[str] = set()
    in_section = False
    cursor = 0
    for line in lines:
        start = description.find(line, cursor)
        cursor = max(start, 0) + len(line) + 1
        normalized_heading = line.strip().rstrip(":").casefold()
        if normalized_heading in REQUIREMENT_HEADINGS:
            in_section = True
            continue
        if in_section and normalized_heading in STOP_HEADINGS:
            in_section = False
            continue
        cleaned = re.sub(r"^[\s•·▪◦*-]+", "", line).strip()
        if not cleaned or cleaned.casefold() in seen:
            continue
        is_signal = bool(REQUIREMENT_SIGNAL.search(cleaned))
        if not in_section and not is_signal:
            continue
        if any(f"{heading}:" in cleaned.casefold() for heading in REQUIREMENT_HEADINGS):
            continue
        if len(cleaned) < 8 or len(cleaned) > 800:
            continue
        actual_start = max(start, 0) + max(line.find(cleaned), 0)
        requirements.append(
            JobRequirement(
                text=cleaned,
                required="preferred" not in cleaned.casefold(),
                source_span=SourceSpan(start=actual_start, end=actual_start + len(cleaned)),
            )
        )
        seen.add(cleaned.casefold())
        if len(requirements) >= MAX_REQUIREMENTS:
            break

    if requirements:
        return requirements

    heading_names = sorted(REQUIREMENT_HEADINGS, key=len, reverse=True)
    heading_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(value) for value in heading_names) + r")\s*:\s*",
        re.IGNORECASE,
    )
    stop_names = sorted(STOP_HEADINGS, key=len, reverse=True)
    stop_pattern = re.compile(
        r"\b(?:" + "|".join(re.escape(value) for value in stop_names) + r")\b",
        re.IGNORECASE,
    )
    heading_match = heading_pattern.search(description)
    section_start = heading_match.end() if heading_match else 0
    stop_match = stop_pattern.search(description, section_start)
    section_end = stop_match.start() if stop_match else len(description)
    section = description[section_start:section_end]
    segments = re.split(r"(?<=[.!?])\s+(?=[A-Z])|\s+" + FLAT_REQUIREMENT_START.pattern, section)
    search_cursor = section_start
    for segment in segments:
        cleaned = segment.strip(" \t\r\n•·▪◦*-")
        if not cleaned or len(cleaned) < 8 or len(cleaned) > 800:
            continue
        if not heading_match and not REQUIREMENT_SIGNAL.search(cleaned):
            continue
        actual_start = description.find(cleaned, search_cursor, section_end)
        if actual_start < 0:
            actual_start = description.find(cleaned, section_start, section_end)
        if actual_start < 0:
            continue
        requirements.append(
            JobRequirement(
                text=cleaned,
                required="preferred" not in cleaned.casefold(),
                source_span=SourceSpan(start=actual_start, end=actual_start + len(cleaned)),
            )
        )
        search_cursor = actual_start + len(cleaned)
        if len(requirements) >= MAX_REQUIREMENTS:
            break
    return requirements


def parse_job_page(source_url: str, resolved_url: str, page_html: str) -> JobPosting:
    parser = _JobHtmlParser()
    parser.feed(page_html)
    posting = _job_posting_json_ld(parser) or {}
    meta_description = _clean_text(
        parser.meta.get("og:description") or parser.meta.get("description") or ""
    )
    title = _string_value(posting.get("title") or posting.get("name"))
    if not title:
        title = _clean_text(parser.meta.get("og:title") or "".join(parser.title_parts))
    company = _organization_name(posting)
    if not company:
        match = re.search(r"Company Name:\s*(.+?)\s+Profession\b", meta_description)
        company = match.group(1).strip() if match else ""
    structured_location = _location(posting)
    match = re.search(r"Location:\s*(.+?)\s+Job ID:\s*", meta_description)
    metadata_location = match.group(1).strip() if match else ""
    location = metadata_location or structured_location
    description = _html_fragment_to_text(_string_value(posting.get("description")))
    if not description:
        marker = re.search(r"Job Description:\s*", meta_description, re.IGNORECASE)
        description = meta_description[marker.end() :] if marker else meta_description
    if not description:
        description = _clean_text("".join(parser.body_parts))
    description = description[:MAX_JOB_DESCRIPTION_CHARS]

    requirements = _requirements_from_description(description)
    canonical_candidate = parser.canonical_url or resolved_url
    canonical_url = _canonicalize_url(urljoin(resolved_url, canonical_candidate))
    warnings: list[str] = []
    if not title:
        warnings.append("Role title could not be extracted")
    if not company:
        warnings.append("Company could not be extracted")
    if not location:
        warnings.append("Location could not be extracted")
    if not requirements:
        warnings.append("Requirements could not be extracted deterministically")
    status = JobIngestionStatus.COMPLETE if not warnings else JobIngestionStatus.NEEDS_REVIEW
    return JobPosting(
        source_url=AnyHttpUrl(source_url),
        canonical_url=AnyHttpUrl(canonical_url),
        resolved_url=AnyHttpUrl(resolved_url),
        title=title,
        company=company,
        location=location,
        description=description,
        description_hash=hashlib.sha256(description.encode()).hexdigest(),
        requirements=requirements,
        platform=_platform_detection(resolved_url),
        status=status,
        warnings=warnings,
        retrieved_at=datetime.now(UTC),
    )


async def _default_resolver(hostname: str) -> list[str]:
    records = await asyncio.to_thread(
        socket.getaddrinfo, hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
    )
    return list(dict.fromkeys(cast(str, record[4][0]) for record in records))


async def _require_public_url(raw_url: str, resolver: HostResolver) -> str:
    parts = urlsplit(raw_url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise JobIngestionError(
            "Only complete HTTP or HTTPS job URLs are supported", code="invalid_url"
        )
    if parts.username or parts.password:
        raise JobIngestionError("Job URLs must not contain credentials", code="invalid_url")
    hostname = parts.hostname.casefold()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        raise JobIngestionError("Local and private-network URLs are blocked", code="unsafe_url")
    try:
        addresses = await resolver(hostname)
    except OSError as error:
        raise JobIngestionError(
            "The job website could not be resolved", code="dns_failed"
        ) from error
    if not addresses:
        raise JobIngestionError("The job website could not be resolved", code="dns_failed")
    for address in addresses:
        parsed = ipaddress.ip_address(address)
        if not parsed.is_global:
            raise JobIngestionError("Local and private-network URLs are blocked", code="unsafe_url")
    return raw_url


class JobIngestionService:
    def __init__(
        self,
        database: Database,
        *,
        client: httpx.AsyncClient | None = None,
        resolver: HostResolver = _default_resolver,
    ) -> None:
        self.database = database
        self.client = client
        self.resolver = resolver

    @staticmethod
    async def _fetch_page(client: httpx.AsyncClient, url: str) -> _FetchedPage:
        async with client.stream("GET", url) as response:
            content_length = response.headers.get("content-length")
            if (
                content_length
                and content_length.isdigit()
                and int(content_length) > MAX_JOB_PAGE_BYTES
            ):
                raise JobIngestionError(
                    "The job page is too large to inspect safely", code="page_too_large"
                )
            content = bytearray()
            if response.status_code not in {301, 302, 303, 307, 308}:
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_JOB_PAGE_BYTES:
                        raise JobIngestionError(
                            "The job page is too large to inspect safely", code="page_too_large"
                        )
            encoding = response.charset_encoding or "utf-8"
            return _FetchedPage(
                status_code=response.status_code,
                headers=httpx.Headers(response.headers),
                url=str(response.url),
                text=content.decode(encoding, errors="replace"),
            )

    async def ingest(self, raw_url: str) -> JobPosting:
        current_url = await _require_public_url(raw_url, self.resolver)
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=httpx.Timeout(30, connect=10),
            follow_redirects=False,
            headers={"User-Agent": "CareerFlow/0.1 (+local supervised job review)"},
        )
        try:
            response: _FetchedPage | None = None
            for _ in range(MAX_REDIRECTS + 1):
                response = await self._fetch_page(client, current_url)
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise JobIngestionError(
                            "The job website returned an invalid redirect", code="redirect_invalid"
                        )
                    current_url = await _require_public_url(
                        urljoin(current_url, location), self.resolver
                    )
                    continue
                break
            else:
                raise JobIngestionError(
                    "The job website redirected too many times", code="redirect_limit"
                )
            if response is None or response.is_redirect:
                raise JobIngestionError(
                    "The job website redirected too many times", code="redirect_limit"
                )
            if response.status_code in {401, 403}:
                raise JobIngestionError(
                    "The job page requires sign-in or blocked automated retrieval",
                    code="access_blocked",
                )
            if response.status_code == 404 or response.status_code == 410:
                raise JobIngestionError(
                    "The job posting is no longer available", code="job_unavailable"
                )
            if response.status_code >= 400:
                raise JobIngestionError(
                    f"The job website returned HTTP {response.status_code}", code="http_error"
                )
            content_type = response.headers.get("content-type", "").casefold()
            if "text/html" not in content_type:
                raise JobIngestionError(
                    "The URL did not return an HTML job page", code="unsupported_content"
                )
            parsed = parse_job_page(raw_url, response.url, response.text)
            return await self.database.save_job_posting(parsed)
        except httpx.TimeoutException as error:
            raise JobIngestionError("The job website timed out", code="timeout") from error
        except httpx.NetworkError as error:
            raise JobIngestionError(
                "The job website could not be reached", code="network_error"
            ) from error
        finally:
            if owns_client:
                await client.aclose()
