"""
routes/search.py — Search Endpoint
------------------------------------
This file handles the HTTP layer for the /search feature.

The route's ONLY jobs are:
  1. Accept the incoming HTTP request
  2. Validate the request body (FastAPI + Pydantic do this automatically)
  3. Get a database session (via Depends)
  4. Call the service to get a result
  5. Return the result as JSON

No business logic lives here. To change HOW the search works (mock data
vs. live RemoteOK API), you only touch services/search_service.py.

Step 4 update: now backed by the RemoteOK public job API instead of
LinkedIn/Playwright. No scraping, no login automation.

Step 5 update: added POST /search/discover-contacts, which looks for
publicly listed recruiting/HR emails on companies' own websites for
jobs already saved in SQLite. No email is ever sent here — that is a
separate, later step.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.job import SearchRequest, SearchResponse, ContactDiscoveryResponse
from app.services.search_service import run_search, run_contact_discovery
from app.db.database import get_db

router = APIRouter(
    prefix="/search",     # All routes in this file start with /search
    tags=["Search"],      # Groups them under "Search" in Swagger /docs
)


@router.post(
    "/",
    response_model=SearchResponse,    # FastAPI validates the return value matches this shape
    summary="Search remote jobs by keyword",
    description=(
        "Accepts a job keyword and returns matching remote jobs from the "
        "RemoteOK public API (or mock data if USE_MOCK_DATA=True). "
        "New jobs are saved to SQLite; duplicates are skipped."
    ),
)
async def search_jobs(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),   # Injects a DB session per request
) -> SearchResponse:
    """
    POST /search/

    Request body:
        { "keyword": "Java Developer Contract" }

    Response:
        {
            "success": true,
            "keyword_searched": "Java Developer Contract",
            "total_results": 3,
            "results": [ { "job_id": "...", "title": "...", ... } ]
        }

    Side effect: any job not already in the database (by RemoteOK ID) is saved.
    """
    result = await run_search(db=db, keyword=request.keyword)
    return result


@router.post(
    "/discover-contacts",
    response_model=ContactDiscoveryResponse,
    summary="Find public recruiter/HR emails for saved jobs",
    description=(
        "For jobs already saved in SQLite that haven't been checked yet, "
        "visits each company's own public website and looks for a "
        "recruiting/HR email on their Careers, Contact, About, Team, or "
        "Jobs pages. Only reads publicly published pages — no login, no "
        "scraping of LinkedIn or any gated content. Does NOT send any email."
    ),
)
async def discover_contacts(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Max number of pending jobs to process in this call",
    ),
    db: AsyncSession = Depends(get_db),
) -> ContactDiscoveryResponse:
    """
    POST /search/discover-contacts?limit=10

    No request body needed — this works off jobs already saved in SQLite
    whose contact_status is still "not_attempted".

    Response:
        {
            "success": true,
            "jobs_processed": 10,
            "emails_found": 4,
            "results": [
                {
                    "job_id": 3,
                    "company": "Acme Corp",
                    "company_website": "https://www.acmecorp.com",
                    "contact_page_url": "https://www.acmecorp.com/careers",
                    "recruiter_email": "careers@acmecorp.com",
                    "contact_status": "found"
                },
                ...
            ]
        }

    Side effect: updates company_website, contact_page_url,
    recruiter_email, and contact_status on each processed Job row.
    """
    result = await run_contact_discovery(db=db, limit=limit)
    return result