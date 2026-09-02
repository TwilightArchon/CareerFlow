from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import httpx
from docx import Document as DocxDocument

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def resume_docx() -> bytes:
    document = DocxDocument()
    document.add_heading("Projects", level=1)
    document.add_paragraph("Built an observable supervised agent.")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


async def test_health_requires_bearer_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["databaseReady"] is True

    response = await client.get("/v1/health", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


async def test_profile_is_saved_versioned_and_restored(client: httpx.AsyncClient) -> None:
    empty = await client.get("/v1/profile")
    assert empty.status_code == 200
    assert empty.json() is None

    request = {
        "expected_version": None,
        "profile": {
            "first_name": "Synthetic",
            "last_name": "Candidate",
            "email": "synthetic.candidate@example.com",
            "city": "Test City",
            "region": "CA",
            "country": "United States",
            "school": "Example University",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science",
            "graduation_year": 2027,
            "work_authorization": "authorized",
            "requires_sponsorship": False,
        },
    }
    saved = await client.put("/v1/profile", json=request)
    assert saved.status_code == 200
    assert saved.json()["profile"]["version"] == 1
    assert all(fact["state"] == "verified" for fact in saved.json()["profile"]["facts"])

    restored = await client.get("/v1/profile")
    assert restored.status_code == 200
    assert restored.json()["profile"] == saved.json()["profile"]

    stale = await client.put("/v1/profile", json=request)
    assert stale.status_code == 409


async def test_resume_import_and_evidence_review_are_authenticated_and_versioned(
    client: httpx.AsyncClient,
) -> None:
    resume = resume_docx()
    created = await client.put(
        "/v1/profile",
        json={
            "expected_version": None,
            "profile": {
                "first_name": "Synthetic",
                "last_name": "Candidate",
                "email": "synthetic.candidate@example.com",
            },
        },
    )
    assert created.status_code == 200

    imported = await client.post(
        "/v1/profile/resume",
        data={"expected_version": "1"},
        files={"file": ("Resume.docx", resume, DOCX_MEDIA_TYPE)},
    )
    assert imported.status_code == 201
    payload = imported.json()
    assert payload["snapshot"]["profile"]["version"] == 2
    assert payload["document"]["status"] == "parsed"
    assert payload["document"]["extractedEvidenceCount"] == 2
    imported_evidence = [
        item
        for item in payload["snapshot"]["profile"]["evidence"]
        if item["sourceDocumentId"] == payload["document"]["id"]
    ]
    assert all(not item["verified"] for item in imported_evidence)

    reviewed = await client.put(
        f"/v1/profile/evidence/{imported_evidence[1]['id']}/verification",
        json={"expected_version": 2, "verified": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["profile"]["version"] == 3
    assert next(
        item
        for item in reviewed.json()["profile"]["evidence"]
        if item["id"] == imported_evidence[1]["id"]
    )["verified"]

    duplicate = await client.post(
        "/v1/profile/resume",
        data={"expected_version": "3"},
        files={"file": ("Resume.docx", resume, DOCX_MEDIA_TYPE)},
    )
    assert duplicate.status_code == 409


async def test_run_transition_is_idempotent(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/v1/runs",
        json={
            "job_id": str(uuid4()),
            "candidate_profile_id": str(uuid4()),
            "candidate_profile_version": 1,
            "auto_submit_authorized": False,
            "job_url": "https://example.com/jobs/1",
            "start_immediately": False,
        },
    )
    assert created.status_code == 201
    run_id = created.json()["id"]
    request = {
        "to_state": "ingesting_job",
        "reason_code": "run_started",
        "idempotency_key": "run-started-key-0001",
    }
    first = await client.post(f"/v1/runs/{run_id}/transitions", json=request)
    second = await client.post(f"/v1/runs/{run_id}/transitions", json=request)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_runs_are_listed_by_recent_activity_with_current_state(
    client: httpx.AsyncClient,
) -> None:
    urls = ["https://example.com/jobs/old", "https://example.com/jobs/new"]
    created_runs: list[dict[str, object]] = []
    for url in urls:
        response = await client.post(
            "/v1/runs",
            json={
                "job_id": str(uuid4()),
                "candidate_profile_id": str(uuid4()),
                "candidate_profile_version": 1,
                "auto_submit_authorized": False,
                "job_url": url,
                "start_immediately": False,
            },
        )
        assert response.status_code == 201
        created_runs.append(response.json())

    transitioned = await client.post(
        f"/v1/runs/{created_runs[0]['id']}/transitions",
        json={
            "to_state": "ingesting_job",
            "reason_code": "test_restore",
            "idempotency_key": "restore-transition-key-0001",
        },
    )
    assert transitioned.status_code == 200

    listed = await client.get("/v1/runs")
    assert listed.status_code == 200
    payload = listed.json()
    assert [run["id"] for run in payload] == [
        created_runs[0]["id"],
        created_runs[1]["id"],
    ]
    assert payload[0]["state"] == "ingesting_job"
    assert payload[0]["jobUrl"] == urls[0]
    assert payload[0]["createdAt"].endswith("Z")
    assert payload[0]["updatedAt"].endswith("Z")


async def test_submission_requires_authorization(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/v1/runs",
        json={
            "job_id": str(uuid4()),
            "candidate_profile_id": str(uuid4()),
            "candidate_profile_version": 1,
            "auto_submit_authorized": False,
            "job_url": "https://example.com/jobs/2",
            "start_immediately": False,
        },
    )
    run_id = created.json()["id"]
    states = [
        "ingesting_job",
        "preparing_materials",
        "opening_application",
        "filling",
        "validating",
        "ready_to_submit",
    ]
    for index, state in enumerate(states):
        response = await client.post(
            f"/v1/runs/{run_id}/transitions",
            json={
                "to_state": state,
                "reason_code": "test",
                "idempotency_key": f"transition-test-key-{index:04d}",
            },
        )
        assert response.status_code == 200

    blocked = await client.post(
        f"/v1/runs/{run_id}/transitions",
        json={
            "to_state": "submitting",
            "reason_code": "test",
            "idempotency_key": "transition-test-key-submit",
        },
    )
    assert blocked.status_code == 409
