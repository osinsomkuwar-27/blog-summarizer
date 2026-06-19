"""
summarizer.py
-------------
Handles AI-powered summarization using the Groq API.
Uses llama-3.3-70b-versatile — fast, free, and highly capable.
"""

import logging
import os
import time
from typing import Optional

from groq import Groq
from groq import RateLimitError, APIStatusError, APIConnectionError

from utils import (
    clean_text,
    count_words,
    is_short_article,
    truncate_text,
    validate_summary,
    MAX_WORDS,
)

logger = logging.getLogger(__name__)

# Groq model — fast and free on the free tier
GROQ_MODEL: str = "llama-3.3-70b-versatile"

# Retry config
MAX_RETRIES: int = 3
RETRY_DELAY: float = 2.0


def _build_prompt(article_text: str) -> str:
    """
    Build a structured prompt for the LLM to generate a high-quality summary.

    Args:
        article_text: Cleaned article text to summarize.

    Returns:
        Complete prompt string.
    """
    return f"""You are a professional technical writer specializing in AI and developer tools.

Your task is to summarize the following blog article clearly and concisely.

STRICT REQUIREMENTS:
- Maximum 300 words total
- Maximum 20 sentences total
- Use clear, professional language
- Write in flowing paragraphs (not bullet points)
- Capture all key concepts, technologies, and takeaways
- Preserve technical accuracy — do not oversimplify
- Begin directly with the summary content (no preambles like "Here is a summary")

ARTICLE TEXT:
\"\"\"
{article_text}
\"\"\"

Write the summary now:"""


def _enforce_word_limit(text: str, max_words: int = MAX_WORDS) -> str:
    """
    Trim text to word limit at the last sentence boundary.

    Args:
        text: Text to trim.
        max_words: Maximum words allowed.

    Returns:
        Trimmed text.
    """
    words = text.split()
    if len(words) <= max_words:
        return text

    truncated = " ".join(words[:max_words])
    last_period = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )
    if last_period > 0:
        return truncated[:last_period + 1].strip()
    return truncated.strip()


def generate_summary(article_text: str) -> Optional[str]:
    """
    Main summarization pipeline using Groq API.

    Steps:
    1. Validate and clean input
    2. Handle short articles
    3. Truncate long input
    4. Call Groq API with retry logic
    5. Validate and enforce output constraints

    Args:
        article_text: Raw article text to summarize.

    Returns:
        Summary string (<=300 words, <=20 sentences), or None on failure.
    """
    # ── Step 1: Validate input ──────────────────────────────────────────────
    if not article_text or not article_text.strip():
        logger.error("Input text is empty. Cannot generate summary.")
        return None

    # ── Step 2: Clean text ──────────────────────────────────────────────────
    cleaned = clean_text(article_text)
    logger.info(f"Cleaned article: {count_words(cleaned)} words.")

    # ── Step 3: Handle short articles ───────────────────────────────────────
    if is_short_article(cleaned):
        logger.info("Article is very short. Returning original text.")
        return cleaned

    # ── Step 4: Truncate if too long ─────────────────────────────────────────
    processed = truncate_text(cleaned)

    # ── Step 5: Check API key ─────────────────────────────────────────────────
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error(
            "GROQ_API_KEY is not set. "
            "Please add it to your .env file."
        )
        return None

    # ── Step 6: Build prompt and call Groq API ────────────────────────────────
    client = Groq(api_key=api_key)
    prompt = _build_prompt(processed)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Calling Groq API (attempt {attempt}/{MAX_RETRIES})...")

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional technical writer. Always follow the user's word and sentence limits exactly.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.3,
                max_tokens=600,
            )

            raw_summary = response.choices[0].message.content.strip()

            if not raw_summary:
                logger.warning("Groq returned an empty response.")
                return None

            logger.info("Groq API call successful.")

            # ── Step 7: Validate and enforce constraints ──────────────────────
            validation = validate_summary(raw_summary)
            logger.info(
                f"Summary stats — Words: {validation['word_count']}, "
                f"Sentences: {validation['sentence_count']}"
            )

            if not validation["valid"]:
                logger.warning(f"Summary exceeded limits: {validation['issues']}")
                raw_summary = _enforce_word_limit(raw_summary)

            return raw_summary

        except RateLimitError as e:
            wait_time = RETRY_DELAY * (2 ** attempt)
            logger.warning(
                f"Rate limit hit (attempt {attempt}). "
                f"Retrying in {wait_time:.1f}s... Error: {e}"
            )
            time.sleep(wait_time)

        except APIConnectionError as e:
            wait_time = RETRY_DELAY * attempt
            logger.warning(
                f"Connection error (attempt {attempt}). "
                f"Retrying in {wait_time:.1f}s... Error: {e}"
            )
            time.sleep(wait_time)

        except APIStatusError as e:
            logger.error(f"Groq API status error: {e.status_code} — {e.message}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error during Groq API call: {e}")
            return None

    logger.error(f"All {MAX_RETRIES} Groq API attempts failed.")
    return None