"""
db/database.py — MongoDB Connection
------------------------------------
Handles the connection between FastAPI and MongoDB.
"""

from pymongo import AsyncMongoClient, ASCENDING

from app.config import settings


# Create the MongoDB client
client = AsyncMongoClient(settings.mongodb_url)

# Select the project database
database = client[settings.mongodb_database]

# Select the jobs collection
jobs_collection = database["jobs"]


async def init_db():
    """
    Test the MongoDB connection and prepare the jobs collection.
    """

    await client.admin.command("ping")

    # Prevent duplicate RemoteOK jobs
    await jobs_collection.create_index(
        [("remoteok_id", ASCENDING)],
        unique=True,
    )

    print("✅ Connected to MongoDB")
    print(f"📦 Database: {settings.mongodb_database}")
    print("📁 Collection: jobs")


async def close_db():
    """
    Close the MongoDB connection when FastAPI shuts down.
    """

    await client.close()


async def get_db():
    """
    Return the jobs collection.

    Routes/services can use this collection to read and write jobs.
    """

    return jobs_collection