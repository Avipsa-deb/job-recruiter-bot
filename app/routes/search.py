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
from app.schemas.job import SearchRequest, SearchResponse, ContactDiscoveryResponse
from app.services.search_service import run_search, run_contact_discovery
from app.db.database import get_db

router = APIRouter(
    prefix="/search",     # All routes in this file start with /search
    tags=["Search"],      # Groups them under "Search" in Swagger /docs
)


@router.post(
    "/",
    response_model=SearchResponse,
    summary="Search remote jobs by keyword",
    description=(
        "Accepts a job keyword and returns matching remote jobs from the "
        "RemoteOK public API. New jobs are saved to MongoDB; duplicates "
        "are skipped."
    ),
)
async def search_jobs(
    request: SearchRequest,
    db=Depends(get_db),
) -> SearchResponse:

    result = await run_search(
        db=db,
        keyword=request.keyword,
    )

    return result


@router.post(
    "/discover-contacts",
    response_model=ContactDiscoveryResponse,
    summary="Find public recruiter/HR emails for saved jobs",
    description=(
        "For jobs already saved in MongoDB that haven't been checked yet, "
        "visits each company's own public website and looks for a "
        "recruiting/HR email on public pages. Does NOT send any email."
    ),
)
async def discover_contacts(
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Max number of pending jobs to process in this call",
    ),
    db=Depends(get_db),
) -> ContactDiscoveryResponse:

    result = await run_contact_discovery(
        db=db,
        limit=limit,
    )

    return result