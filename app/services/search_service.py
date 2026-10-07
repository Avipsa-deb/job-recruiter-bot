"""
services/search_service.py — Search Business Logic
----------------------------------------------------
Handles job searching, MongoDB persistence, and contact discovery.
"""

from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.schemas.job import (
    JobResult,
    SearchResponse,
    ContactDiscoveryResult,
    ContactDiscoveryResponse,
)
from app.services.remoteok_service import search_remoteok_jobs
from app.services.contact_discovery_service import discover_contact_for_job


# ---------------------------------------------------------------------------
# Mock Data
# ---------------------------------------------------------------------------

MOCK_JOBS = [
    {
        "remoteok_id": "mock-1",
        "title": "Java Developer",
        "company": "ABC Corp",
        "location": "Remote",
        "tags": ["java", "backend", "developer"],
        "apply_url": "https://example.com/apply/1",
        "posted_at": "2026-06-19T10:00:00+00:00",
    },
    {
        "remoteok_id": "mock-2",
        "title": "Java Contract Developer",
        "company": "XYZ Ltd",
        "location": "Remote",
        "tags": ["java", "contract", "developer"],
        "apply_url": "https://example.com/apply/2",
        "posted_at": "2026-06-19T11:00:00+00:00",
    },
    {
        "remoteok_id": "mock-3",
        "title": "Senior Java Engineer - Contract",
        "company": "Tech Staffing Inc",
        "location": "Remote",
        "tags": ["java", "senior", "engineer", "contract"],
        "apply_url": "https://example.com/apply/3",
        "posted_at": "2026-06-19T12:00:00+00:00",
    },
    {
        "remoteok_id": "mock-4",
        "title": "Python Backend Developer",
        "company": "Innovate Recruit",
        "location": "Remote",
        "tags": ["python", "backend", "developer"],
        "apply_url": "https://example.com/apply/4",
        "posted_at": "2026-06-19T13:00:00+00:00",
    },
    {
        "remoteok_id": "mock-5",
        "title": "Full Stack Java Developer",
        "company": "Staffing Co",
        "location": "Remote",
        "tags": ["java", "fullstack", "developer"],
        "apply_url": "https://example.com/apply/5",
        "posted_at": "2026-06-19T14:00:00+00:00",
    },
]


def get_mock_jobs(keyword: str) -> list[dict]:
    """
    Filter mock jobs by keyword.
    """

    keyword_lower = keyword.lower()

    matched = [
        job
        for job in MOCK_JOBS
        if any(tag in keyword_lower for tag in job["tags"])
    ]

    return matched if matched else MOCK_JOBS


# ---------------------------------------------------------------------------
# MongoDB Persistence
# ---------------------------------------------------------------------------

async def save_new_jobs(db, jobs: list[dict], keyword: str) -> None:
    """
    Save new jobs to MongoDB.

    Existing RemoteOK IDs are skipped.
    """

    for item in jobs:

        document = {
            "remoteok_id": item["remoteok_id"],
            "title": item["title"],
            "company": item["company"],
            "location": item.get("location"),
            "tags": item.get("tags", []),
            "apply_url": item["apply_url"],
            "keyword_searched": keyword,

            # Contact discovery fields
            "company_website": None,
            "contact_page_url": None,
            "recruiter_email": None,
            "contact_status": "not_attempted",

            # Future feature
            "application_sent": False,

            # When this document was first stored
            "created_at": datetime.now(timezone.utc),
        }

        try:
            await db.insert_one(document)

        except DuplicateKeyError:
            # Same RemoteOK job already exists.
            continue


# ---------------------------------------------------------------------------
# Job Search
# ---------------------------------------------------------------------------

async def run_search(db, keyword: str) -> SearchResponse:
    """
    Search RemoteOK and save new jobs to MongoDB.
    """

    if settings.use_mock_data:
        jobs = get_mock_jobs(keyword)
    else:
        jobs = await search_remoteok_jobs(keyword)

    # Save jobs into MongoDB
    await save_new_jobs(db, jobs, keyword)

    # Convert RemoteOK results into API response objects
    job_results = [
        JobResult(
            job_id=item["remoteok_id"],
            title=item["title"],
            company=item["company"],
            location=item.get("location"),
            tags=item.get("tags", []),
            apply_url=item["apply_url"],
            posted_at=item.get("posted_at"),
            company_website=None,
            contact_page_url=None,
            recruiter_email=None,
            contact_status="not_attempted",
        )
        for item in jobs
    ]

    return SearchResponse(
        success=True,
        keyword_searched=keyword,
        total_results=len(job_results),
        results=job_results,
    )


# ---------------------------------------------------------------------------
# Contact Discovery
# ---------------------------------------------------------------------------

async def run_contact_discovery(
    db,
    limit: int = 10,
) -> ContactDiscoveryResponse:
    """
    Find jobs whose contact discovery has not been attempted yet.

    Discover public company contact information and update MongoDB.
    """

    cursor = (
        db.find({"contact_status": "not_attempted"})
        .limit(limit)
    )

    jobs_to_process = await cursor.to_list(length=limit)

    results: list[ContactDiscoveryResult] = []
    emails_found = 0

    for job in jobs_to_process:

        outcome = await discover_contact_for_job(job["company"])

        update_data = {
            "company_website": outcome["company_website"],
            "contact_page_url": outcome["contact_page_url"],
            "recruiter_email": outcome["recruiter_email"],
            "contact_status": outcome["contact_status"],
        }

        await db.update_one(
            {"_id": job["_id"]},
            {"$set": update_data},
        )

        if outcome["contact_status"] == "found":
            emails_found += 1

        results.append(
            ContactDiscoveryResult(
                job_id=str(job["_id"]),
                company=job["company"],
                company_website=outcome["company_website"],
                contact_page_url=outcome["contact_page_url"],
                recruiter_email=outcome["recruiter_email"],
                contact_status=outcome["contact_status"],
            )
        )

    return ContactDiscoveryResponse(
        success=True,
        jobs_processed=len(results),
        emails_found=emails_found,
        results=results,
    )