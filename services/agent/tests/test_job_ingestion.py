from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from careerflow_agent.config import Settings
from careerflow_agent.database import Database
from careerflow_agent.job_ingestion import JobIngestionError, JobIngestionService, parse_job_page


def job_html(*, requirement: str = "3 years of Python experience required.") -> str:
    description = (
        f"<h2>Qualifications</h2><ul><li>{requirement}</li>"
        "<li>Preferred cloud experience.</li></ul>"
        "<h2>Benefits</h2><p>Health insurance.</p>"
    )
    structured = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "hiringOrganization": {"@type": "Organization", "name": "Example Energy"},
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "addressLocality": "Raleigh",
                    "addressRegion": "NC",
                    "addressCountry": "US",
                },
            },
            "description": description,
        }
    )
    return f"""
    <!doctype html>
    <html>
      <head>
        <link rel="canonical" href="https://jobs.example.com/job/123" />
        <meta property="og:title" content="Fallback title" />
        <script type="application/ld+json">{structured}</script>
      </head>
      <body><h1>Software Engineer</h1></body>
    </html>
    """


def test_structured_job_page_extracts_normalized_fields_and_requirement_spans() -> None:
    posting = parse_job_page(
        "https://tenant.myworkdayjobs.com/jobs/123?utm_source=test",
        "https://tenant.myworkdayjobs.com/jobs/123",
        job_html(),
    )

    assert posting.title == "Software Engineer"
    assert posting.company == "Example Energy"
    assert posting.location == "Raleigh, NC, US"
    assert posting.platform.platform == "workday"
    assert posting.platform.confidence == 0.99
    assert posting.status == "complete"
    assert [item.required for item in posting.requirements] == [True, False]
    assert all(
        posting.description[item.source_span.start : item.source_span.end] == item.text
        for item in posting.requirements
    )
    assert str(posting.canonical_url) == "https://jobs.example.com/job/123"


def test_flattened_workday_metadata_recovers_requirement_section() -> None:
    description = (
        "Location: Raleigh, North Carolina, United States Job ID: R123 "
        "Company Name: Example Energy Profession: Engineering Job Description: "
        "Interns complete meaningful projects. Your Background: "
        "Obtaining a bachelor's degree in engineering "
        "Candidate must have United States work authorization. "
        "Ability to work across cultures. Self-motivated and ability to work independently. "
        "Equal Employment Opportunity Example Energy welcomes all applicants."
    )
    posting = parse_job_page(
        "https://tenant.myworkdayjobs.com/jobs/123",
        "https://tenant.myworkdayjobs.com/jobs/123",
        f'<meta property="og:title" content="Engineering Intern">'
        f'<meta property="og:description" content="{description}">',
    )

    assert posting.location == "Raleigh, North Carolina, United States"
    assert [item.text for item in posting.requirements] == [
        "Obtaining a bachelor's degree in engineering",
        "Candidate must have United States work authorization.",
        "Ability to work across cultures.",
        "Self-motivated and ability to work independently.",
    ]
    assert all(
        posting.description[item.source_span.start : item.source_span.end] == item.text
        for item in posting.requirements
    )


@pytest.mark.asyncio
async def test_ingestion_deduplicates_unchanged_content_and_versions_changes(
    tmp_path: Path,
) -> None:
    settings = Settings(data_dir=tmp_path, local_token="test-token", telemetry_enabled=False)
    database = Database(settings.database_url)
    await database.initialize()
    requirement = "3 years of Python experience required."

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"Location": "/job/123"})
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            text=job_html(requirement=requirement),
        )

    async def public_resolver(_: str) -> list[str]:
        return ["93.184.216.34"]

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = JobIngestionService(database, client=http_client, resolver=public_resolver)
    try:
        first = await service.ingest("https://jobs.example.com/redirect?utm_source=fixture")
        duplicate = await service.ingest("https://jobs.example.com/job/123")
        assert duplicate.id == first.id
        assert duplicate.version == 1

        requirement = "5 years of Python experience required."
        changed = await service.ingest("https://jobs.example.com/job/123")
        assert changed.id != first.id
        assert changed.version == 2
        assert changed.supersedes_id == first.id
        assert (await database.get_job_posting(changed.id)) == changed
    finally:
        await http_client.aclose()
        await database.close()


@pytest.mark.asyncio
async def test_ingestion_blocks_private_network_targets(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path, local_token="test-token", telemetry_enabled=False)
    database = Database(settings.database_url)
    await database.initialize()
    service = JobIngestionService(database)
    try:
        with pytest.raises(JobIngestionError, match="private-network") as captured:
            await service.ingest("http://127.0.0.1/internal-job")
        assert captured.value.code == "unsafe_url"
        with pytest.raises(JobIngestionError, match="must not contain credentials") as credentials:
            await service.ingest("https://candidate:password@example.com/job")
        assert credentials.value.code == "invalid_url"
    finally:
        await database.close()
