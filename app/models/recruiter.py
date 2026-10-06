"""
models/recruiter.py — Recruiter Database Table
--------------------------------------------------
This defines the actual SQL table that stores recruiter/post data.

Important distinction (common beginner confusion):
  - models/recruiter.py   → SQLAlchemy model. Defines the DATABASE TABLE.
  - schemas/search.py     → Pydantic model. Defines the API request/response SHAPE.

They often look similar but serve completely different purposes:
  - Models talk to the database.
  - Schemas talk to the API caller (Swagger, frontend, etc).

Why track 'email_sent'?
  - This is the field Step 5 (Gmail sending) will use to avoid
    emailing the same recruiter twice. We're laying the groundwork now.
"""

from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class Recruiter(Base):
    """
    One row = one recruiter/post combination found during a search.

    Columns:
        id               → auto-incrementing primary key
        recruiter_email  → email extracted from the post (UNIQUE — prevents duplicates)
        job_title        → job title mentioned in the post
        company          → company name
        keyword_searched → which search term found this result (for tracking)
        email_sent       → has an application email already been sent? (Step 5)
        created_at       → timestamp of when this row was first saved
    """

    __tablename__ = "recruiters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # unique=True → the database itself will reject duplicate emails.
    # This is our core "avoid duplicates" safety net at the DB level.
    recruiter_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    keyword_searched: Mapped[str] = mapped_column(String(255), nullable=False)

    # Defaults to False — flipped to True once Step 5 sends the email
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # server_default=func.now() → the DATABASE sets this automatically on insert
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        """Helpful for debugging — shows up when you print a Recruiter object."""
        return f"<Recruiter(email={self.recruiter_email}, company={self.company})>"