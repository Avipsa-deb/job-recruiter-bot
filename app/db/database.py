"""
db/database.py — Database Connection & Session Setup
-------------------------------------------------------
This file sets up the connection to SQLite using SQLAlchemy's ASYNC engine.

Key concepts for beginners:
  - ENGINE: the actual connection to the database file (recruiter_bot.db)
  - SESSION: a temporary "workspace" you use to read/write data, then close
  - Base: the parent class all our table models (models/recruiter.py) inherit from

Why async?
  - FastAPI is async by design. Using async DB calls means your server
    can handle many requests at once without blocking on database I/O.

This file does NOT contain any tables or business logic — just plumbing.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    """
    The base class every database model (table) must inherit from.
    SQLAlchemy uses this to discover all your tables and build the schema.
    """
    pass


# ─── Engine ───────────────────────────────────────────────────────────────
# The engine manages the actual connection to recruiter_bot.db
# echo=settings.debug → prints every SQL query to the terminal (handy for learning!)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

# ─── Session Factory ──────────────────────────────────────────────────────
# This creates new "AsyncSession" objects on demand.
# Each request to the API gets its own session (see get_db() below).
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects usable after commit
)


async def init_db():
    """
    Creates all tables defined in models/ if they don't already exist.
    Called once when the FastAPI app starts up (see main.py).

    Note: This is fine for SQLite + early-stage projects. In a real
    production app with changing schemas, you'd use Alembic migrations
    instead of create_all(). Not needed for this MVP.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    Dependency function that FastAPI injects into routes that need DB access.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...

    The 'yield' pattern ensures the session is always closed after
    the request finishes, even if an error happens.
    """
    async with AsyncSessionLocal() as session:
        yield session