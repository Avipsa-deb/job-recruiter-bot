"""
schemas/search.py — Request & Response Shapes
----------------------------------------------
Pydantic models define the exact shape of data coming IN and going OUT
of your API. FastAPI uses these to:
  1. Validate the request body automatically (wrong type = clear error message)
  2. Generate the schema shown in Swagger docs (/docs)
  3. Serialize your response to JSON

Think of schemas as contracts:
  - SearchRequest  → what the caller MUST send
  - RecruiterResult → what ONE result looks like
  - SearchResponse  → the full response envelope
"""

from pydantic import BaseModel, EmailStr, Field
from typing import List


class SearchRequest(BaseModel):
    """
    The JSON body the caller sends to POST /search.

    Example request body:
        { "keyword": "Java Developer" }
    """
    keyword: str = Field(
        ...,                              # ... means this field is REQUIRED
        min_length=2,                     # Must be at least 2 characters
        max_length=100,                   # No absurdly long strings
        description="Job keyword to search for (e.g. 'Java Developer Contract')",
        examples=["Java Developer Contract"],
    )


class RecruiterResult(BaseModel):
    """
    Represents a single recruiter found in a LinkedIn post.
    In Step 1 this is mock data. In later steps, Playwright fills these.
    """
    recruiter_email: EmailStr = Field(
        ..., description="Email address extracted from the LinkedIn post"
    )
    job_title: str = Field(
        ..., description="Job title mentioned in the post"
    )
    company: str = Field(
        ..., description="Company name from the post"
    )


class SearchResponse(BaseModel):
    """
    The full JSON envelope returned by POST /search.

    Example response:
        {
            "success": true,
            "keyword_searched": "Java Developer",
            "total_results": 2,
            "results": [ {...}, {...} ]
        }
    """
    success: bool = Field(..., description="Whether the search completed without errors")
    keyword_searched: str = Field(..., description="The keyword that was searched")
    total_results: int = Field(..., description="Number of recruiters found")
    results: List[RecruiterResult] = Field(..., description="List of recruiter results")