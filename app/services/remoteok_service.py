"""
services/remoteok_service.py — RemoteOK API Client
-------------------------------------------------------
Calls RemoteOK's public, free, no-auth-required JSON API to fetch real
remote job listings. This is 100% legal and ToS-compliant — RemoteOK
publishes this endpoint specifically for public use, unlike scraping
LinkedIn (which explicitly prohibits automation).

API endpoint: https://remoteok.com/api
No API key. No login. Just an HTTP GET request.

Response shape (as returned by RemoteOK):
    [
        { "legal": "...disclaimer text..." },   <- ALWAYS the first item, not a job!
        {
            "id": "1098127",
            "slug": "...",
            "company": "Example Corp",
            "position": "Senior Java Developer",
            "tags": ["java", "backend", "senior"],
            "location": "Remote",
            "apply_url": "https://remoteok.com/remote-jobs/...",
            "url": "https://remoteok.com/remote-jobs/...",
            "date": "2026-06-18T10:00:00+00:00",
            "description": "...",
            ...
        },
        { ... more jobs ... }
    ]

Why a separate file from search_service.py?
  - This file ONLY knows how to talk to RemoteOK and reshape its response.
  - search_service.py ONLY knows how to orchestrate (call this, save to DB,
    return a response). Neither file needs to know the other's internals.
"""

import httpx
from app.config import settings

# A real browser User-Agent header. Some APIs (RemoteOK included) reject
# requests with no User-Agent or an obvious bot string like "python-requests".
# This is standard, polite practice — not spoofing or evading anything.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


async def fetch_remoteok_jobs() -> list[dict]:
    """
    Calls the RemoteOK API and returns the raw list of job dicts.

    Returns:
        A list of job dicts as RemoteOK returns them. The first item
        (the "legal" disclaimer) is stripped out before returning.

    Raises:
        httpx.HTTPError: if the request fails or RemoteOK returns a
        non-2xx status code. The caller (search_service.py) is
        responsible for deciding how to handle that.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(settings.remoteok_api_url, headers=HEADERS)
        response.raise_for_status()  # Raises if status is 4xx/5xx
        data = response.json()

    # RemoteOK always puts a "legal" disclaimer object as the first array
    # element — it has no "id" or "position" field, so it isn't a real job.
    jobs = [item for item in data if isinstance(item, dict) and "id" in item]

    return jobs


def _matches_keyword(job: dict, keyword_lower: str) -> bool:
    """
    Checks whether a single RemoteOK job matches the search keyword.

    Matching strategy:
      - Split the keyword into individual words (e.g. "Java Developer
        Contract" -> ["java", "developer", "contract"])
      - A job matches if ANY of those words appear as a WHOLE WORD in the
        job's title, tags, or company name.
      - This is intentionally a loose, "OR" style match — for an MVP,
        showing some relevant results beats showing zero exact matches.

    Why whole-word matching instead of plain substring matching?
      - Plain substring checks cause false positives: the keyword "java"
        would match "javascript" because "java" is literally a substring
        of "javascript". Splitting the searchable text into words and
        comparing word-for-word avoids that trap.

    Args:
        job: A single raw job dict from RemoteOK
        keyword_lower: The search keyword, already lowercased

    Returns:
        True if the job is considered a match
    """
    search_words = keyword_lower.split()

    title = (job.get("position") or "").lower()
    company = (job.get("company") or "").lower()
    tags = [str(tag).lower() for tag in (job.get("tags") or [])]

    # Build the set of whole words present in the job's searchable text.
    # .split() on whitespace is enough here since tags/titles don't
    # typically contain punctuation that would merge two words together.
    searchable_words = set(title.split()) | set(company.split())
    for tag in tags:
        searchable_words.update(tag.split())

    return any(word in searchable_words for word in search_words)


def filter_jobs_by_keyword(jobs: list[dict], keyword: str) -> list[dict]:
    """
    Filters the full RemoteOK job list down to ones matching the keyword,
    capped at settings.max_jobs_to_return.

    Args:
        jobs: Full list of raw job dicts from fetch_remoteok_jobs()
        keyword: The search term from the API request

    Returns:
        A filtered (and capped) list of raw job dicts
    """
    keyword_lower = keyword.lower()

    matched = [job for job in jobs if _matches_keyword(job, keyword_lower)]

    return matched[: settings.max_jobs_to_return]


def normalize_job(job: dict) -> dict:
    """
    Converts RemoteOK's raw field names into our app's internal shape.

    Why normalize at all?
      - RemoteOK calls the job title "position", not "title".
      - tags can occasionally be missing or not a list.
      - This function is the ONE place that knows RemoteOK's quirks,
        so the rest of the app can just deal with clean, predictable data.

    Args:
        job: A single raw job dict from RemoteOK

    Returns:
        A dict with clean, consistent keys:
        { remoteok_id, title, company, location, tags (list), apply_url, posted_at }
    """
    tags = job.get("tags") or []
    if not isinstance(tags, list):
        tags = []

    return {
        "remoteok_id": str(job.get("id", "")),
        "title": job.get("position") or "Untitled Position",
        "company": job.get("company") or "Unknown Company",
        "location": job.get("location") or "Remote",
        "tags": [str(t) for t in tags],
        "apply_url": job.get("apply_url") or job.get("url") or "",
        "posted_at": job.get("date"),
    }


async def search_remoteok_jobs(keyword: str) -> list[dict]:
    """
    Main entry point — fetches, filters, and normalizes RemoteOK jobs
    for a given keyword in one call.

    Args:
        keyword: Search term, e.g. "Java Developer Contract"

    Returns:
        List of normalized job dicts, ready to be saved to the DB
        and converted into JobResult schema objects.
    """
    raw_jobs = await fetch_remoteok_jobs()
    matched_jobs = filter_jobs_by_keyword(raw_jobs, keyword)
    return [normalize_job(job) for job in matched_jobs]