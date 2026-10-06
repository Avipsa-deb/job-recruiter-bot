"""
services/search_service.py — Search Business Logic
----------------------------------------------------
The SERVICE layer contains the actual logic of your feature.

Why separate services from routes?
  - Routes handle HTTP (request in -> response out). That's it.
  - Services handle WHAT to do with that request.
  - This separation means you can call the same logic from a route,
    a CLI script, a test, or a scheduled job - without duplicating code.

Step 5 update (this version):
  - Added run_contact_discovery(): for jobs already saved in SQLite,
    visits the company's own public website and looks for a publicly
    listed recruiting/HR email on Careers/Contact/About/Team/Jobs pages.
  - This does NOT scrape LinkedIn and does NOT send any emails — it only
    reads pages a company has published for the public, the same way a
    human applicant would when researching where to send a resume.
  - Every job is updated with a contact_status so nothing is silently
    skipped: "found", "no_website", "no_email_found", or "error".
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.job import JobResult, SearchResponse, ContactDiscoveryResult, ContactDiscoveryResponse
from app.models.job import Job
from app.services.remoteok_service import search_remoteok_jobs
from app.services.contact_discovery_service import discover_contact_for_job

# --- Mock Data Pool --------------------------------------------------------
# Used only when settings.use_mock_data=True (.env). Keeps the SAME shape
# that normalize_job() in remoteok_service.py produces, so save_new_jobs()
# and the rest of the pipeline don't need separate code paths.
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
    Filters the mock pool to return only records that match the keyword.
    Same matching style as the old version: any tag found in the keyword
    counts as a match. Falls back to ALL mock jobs if nothing matches,
    so a demo never returns an empty list.
    """
    keyword_lower = keyword.lower()

    matched = [
        job for job in MOCK_JOBS
        if any(tag in keyword_lower for tag in job["tags"])
    ]

    return matched if matched else MOCK_JOBS


async def save_new_jobs(db: AsyncSession, jobs: list[dict], keyword: str) -> None:
    """
    Saves job records to SQLite, skipping any remoteok_id already stored.

    Why check first instead of letting the DB reject duplicates?
      - The Job model has unique=True on remoteok_id, which WOULD raise
        an error on a duplicate insert. Checking first keeps the logic
        explicit and avoids try/except noise for a beginner project.

    Args:
        db: The active database session (injected by FastAPI via Depends)
        jobs: List of normalized job dicts (from RemoteOK or mock data)
        keyword: The keyword that produced these results (saved for tracking)
    """
    for item in jobs:
        existing = await db.execute(
            select(Job).where(Job.remoteok_id == item["remoteok_id"])
        )
        already_exists = existing.scalar_one_or_none()

        if already_exists is None:
            new_job = Job(
                remoteok_id=item["remoteok_id"],
                title=item["title"],
                company=item["company"],
                location=item.get("location"),
                tags=",".join(item.get("tags", [])),
                apply_url=item["apply_url"],
                keyword_searched=keyword,
            )
            db.add(new_job)

    # Commit writes all new rows to recruiter_bot.db in one go
    await db.commit()


async def run_search(db: AsyncSession, keyword: str) -> SearchResponse:
    """
    Main entry point called by the route.

    Steps:
      1. Get jobs - either from RemoteOK's live API or mock data,
         depending on settings.use_mock_data
      2. Save any NEW jobs to SQLite (duplicates are skipped)
      3. Convert raw dicts -> JobResult Pydantic models
      4. Wrap everything in a SearchResponse envelope

    Args:
        db: Active async DB session, injected by the route
        keyword: Job keyword from the API request

    Returns:
        SearchResponse - the fully structured response object
    """
    if settings.use_mock_data:
        jobs = get_mock_jobs(keyword)
    else:
        jobs = await search_remoteok_jobs(keyword)

    # Persist new jobs to SQLite (existing remoteok_ids are silently skipped)
    await save_new_jobs(db, jobs, keyword)

    # Convert each plain dict into a typed JobResult object.
    # Contact fields default to "not_attempted" here — discovery is a
    # separate step (run_contact_discovery), not part of every search.
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


async def run_contact_discovery(db: AsyncSession, limit: int = 10) -> ContactDiscoveryResponse:
    """
    Finds jobs in SQLite that haven't had contact discovery attempted yet
    (contact_status == "not_attempted"), and for each one, visits the
    company's public website looking for a recruiting/HR email.

    Why work off the database instead of taking jobs as a parameter?
      - Contact discovery is meant to run AFTER a search has already
        saved jobs. This keeps the two steps independent: you can search
        many times, then run discovery once on everything pending.

    Args:
        db: Active async DB session, injected by the route
        limit: Max number of jobs to process in this call (keeps each
               request fast and avoids hammering many company sites at once)

    Returns:
        ContactDiscoveryResponse summarizing what was found
    """
    pending = await db.execute(
        select(Job).where(Job.contact_status == "not_attempted").limit(limit)
    )
    jobs_to_process = pending.scalars().all()

    results: list[ContactDiscoveryResult] = []
    emails_found = 0

    for job in jobs_to_process:
        outcome = await discover_contact_for_job(job.company)

        # Update the row in place — SQLAlchemy tracks this change and
        # writes it on commit() below.
        job.company_website = outcome["company_website"]
        job.contact_page_url = outcome["contact_page_url"]
        job.recruiter_email = outcome["recruiter_email"]
        job.contact_status = outcome["contact_status"]

        if outcome["contact_status"] == "found":
            emails_found += 1

        results.append(
            ContactDiscoveryResult(
                job_id=job.id,
                company=job.company,
                company_website=job.company_website,
                contact_page_url=job.contact_page_url,
                recruiter_email=job.recruiter_email,
                contact_status=job.contact_status,
            )
        )

    # Commit all updates from this batch in one go
    await db.commit()

    return ContactDiscoveryResponse(
        success=True,
        jobs_processed=len(results),
        emails_found=emails_found,
        results=results,
    )