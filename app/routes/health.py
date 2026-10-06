"""
routes/health.py — Health Check Endpoint
-----------------------------------------
A simple endpoint to verify the server is running.

Why have a health check?
  - Every production API has one.
  - It lets you quickly confirm the server started correctly.
  - It returns your app name, version, and status — useful for debugging.
  - No database or LinkedIn logic here — it's intentionally lightweight.
"""

from fastapi import APIRouter
from app.config import settings

# APIRouter is like a "mini FastAPI app" for a specific group of routes.
# We'll create one router per feature (health, linkedin, gmail, etc.)
# and register them all in main.py
router = APIRouter(
    prefix="/health",   # All routes in this file start with /health
    tags=["Health"],    # Groups them under "Health" in the API docs
)


@router.get("/")
async def health_check():
    """
    GET /health/
    Returns the current status of the API server.
    """
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "message": "LinkedIn Recruiter Bot is running!",
    }