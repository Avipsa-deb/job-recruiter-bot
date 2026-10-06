"""
schemas/job.py — RemoteOK Job Shapes
----------------------------------------
Defines what a "job" looks like as it moves through the app.

Why a new schema file instead of reusing schemas/search.py?
  - search.py was built for the old "recruiter email from a post" idea.
  - A job aggregator returns genuinely different data: job title, company,
    a real apply URL, tags, location, salary — no "email" concept at all.
  - Keeping this in its own file makes the RemoteOK feature self-contained
    and easy to find.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class JobResult(BaseModel):
    """
    One job listing, shaped for API responses.
    This is what the caller (Swagger, a frontend, etc.) actually sees.
    """
    job_id: str = Field(..., description="RemoteOK's unique ID for this job")
    title: str = Field(..., description="Job title, e.g. 'Senior Java Developer'")
    company: str = Field(..., description="Hiring company name")
    location: Optional[str] = Field(None, description="Location or 'Remote'")
    tags: List[str] = Field(default_factory=list, description="Skill/role tags")
    apply_url: str = Field(..., description="Direct link to apply for this job")
    posted_at: Optional[str] = Field(None, description="ISO date the job was posted")

    # ─── Contact Discovery fields (Step 5) ───────────────────
    company_website: Optional[str] = Field(None, description="Discovered company homepage, if found")
    contact_page_url: Optional[str] = Field(None, description="Page the email was found on, if any")
    recruiter_email: Optional[str] = Field(None, description="Publicly listed recruiting/HR email, if found")
    contact_status: str = Field(
        "not_attempted",
        description="not_attempted | no_website | no_email_found | found | error",
    )


class ContactDiscoveryResult(BaseModel):
    """
    One job's contact-discovery outcome, returned by POST /search/discover-contacts.
    """
    job_id: int = Field(..., description="Internal database ID of the job")
    company: str = Field(..., description="Company name")
    company_website: Optional[str] = Field(None, description="Discovered company homepage, if found")
    contact_page_url: Optional[str] = Field(None, description="Page the email was found on, if any")
    recruiter_email: Optional[str] = Field(None, description="Publicly listed recruiting/HR email, if found")
    contact_status: str = Field(..., description="not_attempted | no_website | no_email_found | found | error")


class ContactDiscoveryResponse(BaseModel):
    """
    The full JSON envelope returned by POST /search/discover-contacts.
    """
    success: bool = Field(..., description="Whether the discovery batch completed without crashing")
    jobs_processed: int = Field(..., description="How many jobs were attempted in this run")
    emails_found: int = Field(..., description="How many of those jobs resulted in a found email")
    results: List[ContactDiscoveryResult] = Field(..., description="Per-job discovery outcomes")


class SearchRequest(BaseModel):
    """
    The JSON body the caller sends to POST /search.
    Example: { "keyword": "Java Developer Contract" }
    """
    keyword: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Job keyword to search for (matched against title/tags/description)",
        examples=["Java Developer Contract"],
    )


class SearchResponse(BaseModel):
    """
    The full JSON envelope returned by POST /search.
    """
    success: bool = Field(..., description="Whether the search completed without errors")
    keyword_searched: str = Field(..., description="The keyword that was searched")
    total_results: int = Field(..., description="Number of jobs returned")
    results: List[JobResult] = Field(..., description="List of matching jobs")