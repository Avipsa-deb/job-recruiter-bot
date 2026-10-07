"""
config.py — Application Configuration
--------------------------------------
Loads all environment variables from the .env file using Pydantic Settings.

Why Pydantic Settings?
  - Automatically reads from .env file
  - Validates types (e.g., DEBUG must be a bool, not just any string)
  - Gives you a single place to manage all config — no scattered os.getenv() calls
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── App ────────────────────────────────────────────────
    app_name: str = "LinkedIn Recruiter Bot"
    app_version: str = "1.0.0"
    debug: bool = True

    # ─── Job Aggregator (RemoteOK) ───────────────────────────
    remoteok_api_url: str = "https://remoteok.com/api"
    use_mock_data: bool = True
    max_jobs_to_return: int = 20

    # ─── Contact Discovery ────────────────────────────────────
    contact_discovery_timeout_seconds: int = 8
    contact_discovery_page_keywords: str = "careers,jobs,contact,about,team,hiring"
    contact_discovery_max_pages_per_company: int = 4
    contact_discovery_delay_seconds: float = 1.0

    # ─── Database ───────────────────────────────────────────
    mongodb_url: str = "mongodb://127.0.0.1:27017"
    mongodb_database: str = "job_recruiter_db"



    # ─── Resume ─────────────────────────────────────────────
    resume_file_path: str = "resume.pdf"

    class Config:
        # Tell Pydantic to look for a file called ".env" in the project root
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single instance that the rest of the app imports
# Usage: from app.config import settings
settings = Settings()