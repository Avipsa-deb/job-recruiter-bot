"""
main.py — FastAPI Application Entry Point
------------------------------------------
This is the heart of the application. FastAPI starts here.

What this file does:
  1. Creates the FastAPI app instance
  2. Registers all routers (groups of related endpoints)
  3. Adds startup/shutdown lifecycle events (e.g., connect to DB on start)
  4. Configures metadata shown in the auto-generated API docs

How to run:
  uvicorn app.main:app --reload
  
  Breakdown:
    - app.main     → the file is app/main.py
    - :app         → the FastAPI instance is named `app`
    - --reload     → auto-restarts the server when you save a file (dev only)
"""

from fastapi import FastAPI
from app.config import settings
from app.routes import health
from app.routes import search
from app.db.database import init_db, close_db
  


def create_app() -> FastAPI:
    """
    Factory function that builds and configures the FastAPI app.
    Using a factory makes it easy to create test instances later.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Searches remote job listings via the RemoteOK public API "
            "and tracks application status. No scraping, no LinkedIn automation."
        ),
        # Swagger UI lives at http://localhost:8000/docs
        docs_url="/docs",
        # ReDoc (alternative docs UI) lives at http://localhost:8000/redoc
        redoc_url="/redoc",
    )

    # ─── Register Routers ────────────────────────────────────────
   # Each router handles a specific feature area.
    app.include_router(health.router)
    app.include_router(search.router)   # ← NEW in Step 2

    # ─── Lifecycle Events ────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup():
        await init_db()

        print(f"✅ {settings.app_name} v{settings.app_version} started")
        print("📖 Docs available at: http://localhost:8000/docs")

    @app.on_event("shutdown")
    async def on_shutdown():
        await close_db()
        print("🛑 Server shutting down...")

    return app


# Create the app instance — uvicorn imports this
app = create_app()