# Job Recruiter Bot

A job discovery and company contact discovery platform built with FastAPI.

The application searches real remote job listings using the RemoteOK public API, stores job information in a database, and can discover publicly available company contact information from company websites.

## Features

- Search remote jobs using keywords
- Fetch real job listings from the RemoteOK public API
- Store job information
- Prevent duplicate job records
- Discover company websites
- Search public company pages such as:
  - Careers
  - Jobs
  - Contact
  - About
  - Team
  - Hiring
- Extract publicly listed contact emails when available
- Track contact discovery status
- FastAPI backend with automatic Swagger documentation

## Architecture

```text
User
  ↓
FastAPI
  ↓
RemoteOK API
  ↓
Job Search
  ↓
Database
  ↓
Contact Discovery
  ↓
Company Website
  ↓
Public Contact Information