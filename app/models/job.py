"""
models/job.py — Job Database Table
----------------------------------------
Defines the actual SQL table that stores jobs pulled from RemoteOK,
plus any recruiter contact info discovered from the company's website.

Important distinction (common beginner confusion):
  - models/job.py     → SQLAlchemy model. Defines the DATABASE TABLE.
  - schemas/job.py    → Pydantic model. Defines the API request/response SHAPE.

Why store remoteok_id separately from our own auto-increment id?
  - RemoteOK gives every job a stable ID (e.g. "1098127"). We use THAT,
    not the job title or company, as our duplicate-detection key. Two
    different jobs can share a title ("Java Developer"), but RemoteOK's
    ID is guaranteed unique per listing — exactly what we need to avoid
    inserting the same job twice across repeated searches.

Step 5 update:
  - Added columns for the company-contact-discovery feature:
    company_website, contact_page_url, recruiter_email, contact_status.
  - Jobs are ALWAYS saved even if no email is found — contact_status
    records why (e.g. "not_attempted", "no_website", "no_email_found",
    "found"). This means nothing is silently dropped.
"""

from sqlalchemy import String, Integer, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Job(Base):
    """
    One row = one job listing pulled from the RemoteOK API.

    Columns:
        id               → auto-incrementing primary key (our own internal ID)
        remoteok_id      → RemoteOK's own unique job ID (UNIQUE — prevents duplicates)
        title            → job title, e.g. "Senior Java Developer"
        company          → hiring company name
        location         → location string, often "Remote"
        tags             → comma-separated tags (SQLite has no native array type)
        apply_url        → direct link to apply
        keyword_searched → which search term surfaced this job (for tracking)

        company_website  → best-guess homepage URL for the hiring company
        contact_page_url → the specific page an email was found on (Careers/Contact/etc.)
        recruiter_email  → publicly listed email found on the company's site, if any
        contact_status   → "not_attempted" | "no_website" | "no_email_found" | "found" | "error"

        application_sent → has an application email already been sent? (future step)
        created_at       → timestamp of when this row was first saved
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # unique=True → the database itself rejects duplicate RemoteOK jobs.
    remoteok_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)

    # Stored as a comma-separated string (e.g. "java,backend,contract").
    # SQLite doesn't have a native list/array column type, and for an
    # MVP this is simpler than a separate tags table with a join.
    tags: Mapped[str] = mapped_column(Text, nullable=True)

    apply_url: Mapped[str] = mapped_column(String(500), nullable=False)
    keyword_searched: Mapped[str] = mapped_column(String(255), nullable=False)

    # ─── Contact Discovery (Step 5) ──────────────────────────
    company_website: Mapped[str] = mapped_column(String(500), nullable=True)
    contact_page_url: Mapped[str] = mapped_column(String(500), nullable=True)
    recruiter_email: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # Tracks WHY a job does or doesn't have an email — never just silent.
    # Default "not_attempted" means contact discovery hasn't run yet for this job.
    contact_status: Mapped[str] = mapped_column(String(50), default="not_attempted", nullable=False)

    # Defaults to False — flipped to True only after a real send (Step 6)
    application_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Job(title={self.title}, company={self.company}, contact_status={self.contact_status})>"