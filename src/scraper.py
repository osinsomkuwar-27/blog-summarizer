"""
scraper.py
----------
Responsible for fetching and extracting clean article text from a given URL.
Uses requests for HTTP and BeautifulSoup for HTML parsing.
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Configure module-level logger
logger = logging.getLogger(__name__)

# HTTP request timeout in seconds
REQUEST_TIMEOUT: int = 15

# Common headers to mimic a real browser and avoid bot-blocking
HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# HTML tags that typically contain the main article body
CONTENT_TAGS: list[str] = ["article", "main", "section", "div"]

# CSS classes/IDs commonly associated with blog content
CONTENT_IDENTIFIERS: list[str] = [
    "post-content", "article-body", "entry-content",
    "blog-content", "content", "post", "article",
]


def is_valid_url(url: str) -> bool:
    """
    Validate whether the given string is a properly formatted HTTP/HTTPS URL.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL is valid, False otherwise.
    """
    pattern = re.compile(
        r'^(https?://)'                        # must start with http:// or https://
        r'(([a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,})'  # domain name
        r'(:\d+)?'                             # optional port
        r'(/[^\s]*)?$'                         # optional path
    )
    return bool(pattern.match(url.strip()))


def fetch_html(url: str) -> Optional[str]:
    """
    Fetch raw HTML content from a URL.

    Args:
        url: The target URL to fetch.

    Returns:
        Raw HTML string if successful, None on network or HTTP errors.

    Raises:
        Does not raise — all exceptions are caught and logged.
    """
    try:
        logger.info(f"Fetching URL: {url}")
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses
        logger.info(f"Successfully fetched URL. Status: {response.status_code}")
        return response.text

    except requests.exceptions.MissingSchema:
        logger.error("Invalid URL: Missing schema (http/https).")
    except requests.exceptions.ConnectionError:
        logger.error("Network error: Unable to connect to the URL.")
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {REQUEST_TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected request error: {e}")

    return None


def extract_text_from_html(html: str) -> Optional[str]:
    """
    Parse HTML and extract readable article text using BeautifulSoup.

    Strategy:
    1. Try to find semantic article containers (e.g., <article>, <main>).
    2. Fallback to divs with common content-related class names.
    3. If all else fails, extract all paragraph text from the full body.

    Args:
        html: Raw HTML string to parse.

    Returns:
        Cleaned plain text string, or None if nothing useful is found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise: scripts, styles, navigation, footers, ads
    for tag in soup(["script", "style", "nav", "footer", "header",
                      "aside", "form", "noscript", "iframe"]):
        tag.decompose()

    # Strategy 1: Look for semantic article containers
    for tag_name in CONTENT_TAGS:
        container = soup.find(tag_name)
        if container:
            text = container.get_text(separator=" ", strip=True)
            if len(text) > 200:  # Must have meaningful content
                logger.info(f"Extracted text from <{tag_name}> tag.")
                return text

    # Strategy 2: Look for divs with known content class names
    for identifier in CONTENT_IDENTIFIERS:
        container = soup.find("div", {"class": re.compile(identifier, re.I)})
        if not container:
            container = soup.find("div", {"id": re.compile(identifier, re.I)})
        if container:
            text = container.get_text(separator=" ", strip=True)
            if len(text) > 200:
                logger.info(f"Extracted text using identifier '{identifier}'.")
                return text

    # Strategy 3: Fallback — gather all <p> tags from the full body
    paragraphs = soup.find_all("p")
    if paragraphs:
        combined = " ".join(p.get_text(strip=True) for p in paragraphs)
        if len(combined) > 100:
            logger.info("Extracted text from all <p> tags as fallback.")
            return combined

    logger.warning("No extractable article content found in the HTML.")
    return None


def scrape_blog(url: str) -> Optional[str]:
    """
    High-level function to scrape and return clean text from a blog URL.

    This is the main entry point for the scraper module. It validates the URL,
    fetches the HTML, and extracts readable article text.

    Args:
        url: The full URL of the blog/article to scrape.

    Returns:
        Cleaned article text as a string, or None if scraping fails.
    """
    # Step 1: Validate URL format
    if not is_valid_url(url):
        logger.error(f"Invalid URL provided: '{url}'")
        return None

    # Step 2: Fetch HTML
    html = fetch_html(url)
    if html is None:
        logger.error("Failed to retrieve HTML from the URL.")
        return None

    # Step 3: Extract text content
    text = extract_text_from_html(html)
    if text is None:
        logger.error("Failed to extract article text from HTML.")
        return None

    logger.info(f"Scraped article text ({len(text)} characters).")
    return text