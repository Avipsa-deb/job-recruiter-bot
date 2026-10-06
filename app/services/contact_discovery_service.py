"""
services/contact_discovery_service.py — Public Contact Info Discovery
---------------------------------------------------------------------------
Finds a company's own public website and looks for a publicly listed
recruiting/HR email address on common pages (Careers, Contact, About,
Team, Jobs, Hiring).

WHY THIS IS DIFFERENT FROM "SCRAPING LINKEDIN":
  - We never log into anything. No credentials, no session cookies.
  - We only visit a company's OWN public website — pages they published
    specifically for the public to read (their Careers/Contact pages).
  - We respect robots.txt before fetching any page on a domain.
  - We send a small, fixed number of requests per company with a delay
    between them — not a high-volume crawl.
  - This is the same thing a human applicant does manually: visit a
    company site, find a contact email, note it down. We're just
    automating the lookup, not bypassing any access control.

WHAT THIS FILE DOES NOT DO (by design, per Step 5 scope):
  - Does NOT send any emails. That's a future step.
  - Does NOT guess or fabricate an email if none is publicly listed.
  - Does NOT mark anything as "application_sent".

Pipeline for one job:
  1. guess_company_domain()   -> turn "Acme Corp" into a candidate URL
  2. verify_company_website() -> confirm that URL actually responds
  3. check_robots_txt()       -> confirm we're allowed to fetch sub-pages
  4. find_candidate_pages()   -> find links on the homepage matching
                                  careers/contact/about/team/hiring/jobs
  5. extract_email_from_page() -> look for a mailto: link or a plain-text
                                   email address on each candidate page
  6. Return the first email found, plus which page it came from
"""

import asyncio
import re
import urllib.parse
import urllib.robotparser

import httpx
from bs4 import BeautifulSoup

from app.config import settings

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

EMAIL_REGEX = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

# Emails matching these patterns are almost always not useful for a job
# application (privacy/legal/abuse inboxes, image filenames misread as
# emails, etc.) — skip them even if technically a valid-looking address.
IGNORED_EMAIL_PREFIXES = (
    "privacy@", "legal@", "abuse@", "noreply@", "no-reply@",
    "support@", "security@", "webmaster@", "postmaster@",
)


def _slugify_company_name(company: str) -> str:
    """
    Turns a company name into a domain-friendly slug.
    "Acme Corp, Inc." -> "acmecorp"

    This is a best-effort guess, not a guarantee. It strips common
    legal suffixes from the END of the name only, then removes all
    remaining non-alphanumeric characters.

    Why end-anchored regex instead of a simple .replace()?
      - A naive .replace(" corp", "") would also strip " corp" out of
        the MIDDLE of a name (e.g. "Corpwell Inc" -> "well", which is
        wrong). Anchoring the suffix pattern to the end of the string
        avoids that.
      - The suffix must be preceded by a REQUIRED word boundary (space
        or comma) — not just "optional" whitespace — otherwise a name
        like "TestCo" or "Tesco" gets mistaken for "Test" + suffix "co",
        incorrectly stripping real letters that happen to spell a legal
        suffix at the end of a single word.
    """
    name = company.lower().strip()

    # Strip ONE trailing legal suffix, e.g. ", inc.", " llc", " corp" —
    # but ONLY if it's preceded by a space or comma (a real word boundary),
    # never if it's just the tail end of a single fused word like "Tesco".
    name = re.sub(r"[\s,]+(inc\.?|llc|ltd\.?|corp\.?|co\.?)$", "", name)

    # Now strip everything that isn't a letter or digit
    name = re.sub(r"[^a-z0-9]", "", name)
    return name


def guess_company_domain(company: str) -> str | None:
    """
    Builds a best-guess homepage URL from a company name.

    Args:
        company: Company name as returned by RemoteOK (e.g. "Acme Corp")

    Returns:
        A candidate URL like "https://www.acmecorp.com", or None if the
        company name doesn't produce a usable slug (e.g. empty string).
    """
    slug = _slugify_company_name(company)
    if not slug:
        return None
    return f"https://www.{slug}.com"


async def verify_company_website(client: httpx.AsyncClient, url: str) -> str | None:
    """
    Confirms a guessed homepage URL actually resolves and responds.

    Tries the "www." version first, then falls back to the bare domain
    (some companies redirect or don't use the www subdomain at all).

    Args:
        client: Shared httpx client (reused across calls for efficiency)
        url: The candidate homepage URL from guess_company_domain()

    Returns:
        The final URL that actually worked (after following redirects),
        or None if neither variant responded successfully.
    """
    candidates = [url, url.replace("https://www.", "https://")]

    for candidate in candidates:
        try:
            response = await client.get(
                candidate,
                headers=HEADERS,
                timeout=settings.contact_discovery_timeout_seconds,
                follow_redirects=True,
            )
            if response.status_code < 400:
                return str(response.url)
        except httpx.HTTPError:
            continue  # Try the next candidate; this one didn't resolve

    return None


def check_robots_txt(base_url: str, robots_text: str, path: str) -> bool:
    """
    Checks whether our user-agent is allowed to fetch a given path,
    according to the site's own robots.txt rules.

    Why check this at all?
      - robots.txt is a site's explicit, public statement of what
        automated tools may and may not access. Respecting it is the
        baseline standard for any legitimate, polite crawler.

    Args:
        base_url: The site's homepage URL (used to build the robots.txt URL)
        robots_text: The raw text content of robots.txt
        path: The specific path we want to check (e.g. "/careers")

    Returns:
        True if fetching is allowed (or robots.txt is empty/unparseable —
        fail open, since an empty robots.txt means no restrictions stated)
    """
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_text.splitlines())
    full_url = urllib.parse.urljoin(base_url, path)
    return parser.can_fetch(HEADERS["User-Agent"], full_url)


async def _fetch_robots_txt(client: httpx.AsyncClient, base_url: str) -> str:
    """
    Fetches robots.txt for a domain. Returns an empty string if it
    doesn't exist or can't be fetched (treated as "no restrictions").
    """
    robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
    try:
        response = await client.get(
            robots_url, headers=HEADERS,
            timeout=settings.contact_discovery_timeout_seconds,
        )
        if response.status_code == 200:
            return response.text
    except httpx.HTTPError:
        pass
    return ""


def find_candidate_pages(homepage_html: str, base_url: str) -> list[str]:
    """
    Parses the homepage HTML and finds links whose URL or link text
    matches our target keywords (careers, contact, about, team, hiring, jobs).

    Args:
        homepage_html: Raw HTML of the company's homepage
        base_url: The homepage URL (used to resolve relative links like "/careers")

    Returns:
        A de-duplicated list of absolute URLs to check next, capped at
        settings.contact_discovery_max_pages_per_company.
    """
    soup = BeautifulSoup(homepage_html, "html.parser")
    keywords = [kw.strip() for kw in settings.contact_discovery_page_keywords.split(",")]

    found_urls: list[str] = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        link_text = link.get_text(strip=True).lower()
        href_lower = href.lower()

        matches_keyword = any(kw in href_lower or kw in link_text for kw in keywords)
        if not matches_keyword:
            continue

        absolute_url = urllib.parse.urljoin(base_url, href)

        # Skip anything that isn't on the same domain (avoid following
        # links out to unrelated third-party sites like social media).
        if urllib.parse.urlparse(absolute_url).netloc != urllib.parse.urlparse(base_url).netloc:
            continue

        if absolute_url not in seen:
            seen.add(absolute_url)
            found_urls.append(absolute_url)

        if len(found_urls) >= settings.contact_discovery_max_pages_per_company:
            break

    return found_urls


def extract_email_from_html(html: str) -> str | None:
    """
    Looks for a usable email address in a page's HTML.

    Checks two places, in order of reliability:
      1. mailto: links (the clearest, most intentional signal — someone
         deliberately made this email clickable)
      2. Plain text matching the email regex anywhere on the page

    Args:
        html: Raw HTML of a single page (e.g. the Careers page)

    Returns:
        The first usable email found, or None if nothing qualifies.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Check mailto: links first — highest signal
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().startswith("mailto:"):
            email = href.split(":", 1)[1].split("?")[0].strip().lower()
            if email and not email.startswith(IGNORED_EMAIL_PREFIXES):
                return email

    # 2. Fall back to scanning visible text for an email pattern
    page_text = soup.get_text(" ")
    matches = EMAIL_REGEX.findall(page_text)
    for match in matches:
        email_lower = match.lower()
        if not email_lower.startswith(IGNORED_EMAIL_PREFIXES):
            return email_lower

    return None


async def discover_contact_for_job(company: str) -> dict:
    """
    Main entry point — runs the full discovery pipeline for one company.

    Args:
        company: Company name as stored on the Job record

    Returns:
        A dict with the discovery outcome:
        {
            "company_website": str | None,
            "contact_page_url": str | None,
            "recruiter_email": str | None,
            "contact_status": "found" | "no_website" | "no_email_found" | "error",
        }

    This function NEVER raises for normal "couldn't find anything" cases —
    it always returns a result dict so the caller can save it directly to
    the Job row. Unexpected errors are caught and reported via "error"
    status rather than crashing the whole search batch.
    """
    guessed_url = guess_company_domain(company)
    if not guessed_url:
        return {
            "company_website": None,
            "contact_page_url": None,
            "recruiter_email": None,
            "contact_status": "no_website",
        }

    try:
        async with httpx.AsyncClient() as client:
            homepage_url = await verify_company_website(client, guessed_url)
            if not homepage_url:
                return {
                    "company_website": None,
                    "contact_page_url": None,
                    "recruiter_email": None,
                    "contact_status": "no_website",
                }

            # Be polite: small pause before crawling further pages on this domain
            await asyncio.sleep(settings.contact_discovery_delay_seconds)

            robots_text = await _fetch_robots_txt(client, homepage_url)

            homepage_response = await client.get(
                homepage_url, headers=HEADERS,
                timeout=settings.contact_discovery_timeout_seconds,
                follow_redirects=True,
            )
            candidate_pages = find_candidate_pages(homepage_response.text, homepage_url)

            for page_url in candidate_pages:
                if not check_robots_txt(homepage_url, robots_text, page_url):
                    continue  # robots.txt disallows this path — skip it, don't fetch

                await asyncio.sleep(settings.contact_discovery_delay_seconds)

                try:
                    page_response = await client.get(
                        page_url, headers=HEADERS,
                        timeout=settings.contact_discovery_timeout_seconds,
                        follow_redirects=True,
                    )
                except httpx.HTTPError:
                    continue  # This particular sub-page failed; try the next one

                email = extract_email_from_html(page_response.text)
                if email:
                    return {
                        "company_website": homepage_url,
                        "contact_page_url": page_url,
                        "recruiter_email": email,
                        "contact_status": "found",
                    }

            # Homepage and sub-pages were all checked — nothing found
            return {
                "company_website": homepage_url,
                "contact_page_url": None,
                "recruiter_email": None,
                "contact_status": "no_email_found",
            }

    except httpx.HTTPError:
        # Network-level failure (timeout, DNS error, connection refused, etc.)
        return {
            "company_website": None,
            "contact_page_url": None,
            "recruiter_email": None,
            "contact_status": "error",
        }