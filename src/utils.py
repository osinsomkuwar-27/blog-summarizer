"""
utils.py
--------
Utility functions for text preprocessing, word/sentence counting,
output file saving, and logging configuration.
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

MAX_WORDS: int = 300
MAX_SENTENCES: int = 20

# Articles typically under this word count are considered "short"
SHORT_ARTICLE_THRESHOLD: int = 150

# Articles over this character count will be truncated before sending to the API
# Gemini supports large contexts, but we limit to avoid cost/latency issues
MAX_INPUT_CHARS: int = 12_000

# Output directory (relative to project root)
OUTPUT_DIR: Path = Path(__file__).resolve().parent.parent / "outputs"


# ─── Logging Setup ────────────────────────────────────────────────────────────

def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger with console output and a clean format.

    Args:
        level: Logging level (default: INFO).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# ─── Text Preprocessing ───────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Clean and normalize raw scraped text for summarization.

    Operations performed:
    - Collapse multiple whitespace/newlines into single spaces
    - Remove non-printable/control characters
    - Strip leading and trailing whitespace

    Args:
        text: Raw text string from the scraper.

    Returns:
        Cleaned, normalized text string.
    """
    if not text:
        return ""

    # Replace newlines and tabs with spaces
    text = re.sub(r"[\n\r\t]+", " ", text)

    # Remove non-printable characters (keep standard ASCII + common Unicode)
    text = re.sub(r"[^\x20-\x7E\u00A0-\uFFFF]", "", text)

    # Collapse multiple consecutive spaces into one
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def count_words(text: str) -> int:
    """
    Count the number of words in a text string.

    Args:
        text: Input text.

    Returns:
        Integer word count.
    """
    return len(text.split()) if text.strip() else 0


def count_sentences(text: str) -> int:
    """
    Count the approximate number of sentences using punctuation heuristics.

    Splits on '.', '!', '?' followed by whitespace or end-of-string.

    Args:
        text: Input text.

    Returns:
        Integer sentence count.
    """
    if not text.strip():
        return 0
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return len([s for s in sentences if s.strip()])


def truncate_text(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """
    Truncate text to a maximum number of characters, breaking at a word boundary.

    This prevents sending excessively long articles to the API, which could
    increase cost and latency. The truncation is done at a word boundary to
    avoid cutting mid-word.

    Args:
        text: Input text to truncate.
        max_chars: Maximum character limit (default: MAX_INPUT_CHARS).

    Returns:
        Truncated text string.
    """
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Walk back to the last space to avoid cutting a word in half
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    logging.getLogger(__name__).warning(
        f"Input text truncated from {len(text)} to {len(truncated)} characters "
        f"(limit: {max_chars})."
    )
    return truncated


def is_short_article(text: str) -> bool:
    """
    Determine if the article is shorter than the summary limit itself.

    If the article is under SHORT_ARTICLE_THRESHOLD words, summarizing it
    would produce a result longer than the original — we return it as-is.

    Args:
        text: Article text.

    Returns:
        True if the article is considered "short", False otherwise.
    """
    return count_words(text) <= SHORT_ARTICLE_THRESHOLD


def validate_summary(summary: str) -> dict[str, object]:
    """
    Validate that the generated summary meets the required constraints.

    Constraints:
    - Maximum 300 words
    - Maximum 20 sentences

    Args:
        summary: Generated summary text.

    Returns:
        Dictionary with keys:
        - 'valid' (bool): True if all constraints are met.
        - 'word_count' (int): Number of words in the summary.
        - 'sentence_count' (int): Number of sentences in the summary.
        - 'issues' (list[str]): List of constraint violations (empty if valid).
    """
    word_count = count_words(summary)
    sentence_count = count_sentences(summary)
    issues = []

    if word_count > MAX_WORDS:
        issues.append(f"Exceeds word limit: {word_count}/{MAX_WORDS} words.")
    if sentence_count > MAX_SENTENCES:
        issues.append(f"Exceeds sentence limit: {sentence_count}/{MAX_SENTENCES} sentences.")

    return {
        "valid": len(issues) == 0,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "issues": issues,
    }


# ─── File I/O ─────────────────────────────────────────────────────────────────

def save_summary(summary: str, filename: str = "generated_summary.txt") -> Path:
    """
    Save the generated summary to the outputs/ directory.

    Creates the output directory if it does not exist. Prepends a metadata
    header (timestamp, word count, sentence count) to the saved file.

    Args:
        summary: The summary text to save.
        filename: Output filename (default: 'generated_summary.txt').

    Returns:
        Path object pointing to the saved file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename

    word_count = count_words(summary)
    sentence_count = count_sentences(summary)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = (
        f"# Blog Summary\n"
        f"# Generated: {timestamp}\n"
        f"# Words: {word_count} / {MAX_WORDS}\n"
        f"# Sentences: {sentence_count} / {MAX_SENTENCES}\n"
        f"# {'VALID' if word_count <= MAX_WORDS and sentence_count <= MAX_SENTENCES else 'EXCEEDS LIMITS'}\n"
        f"{'─' * 60}\n\n"
        f"{summary}\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logging.getLogger(__name__).info(f"Summary saved to: {output_path}")
    return output_path


def read_text_file(filepath: str) -> Optional[str]:
    """
    Read and return the contents of a plain text file.

    Args:
        filepath: Path to the text file.

    Returns:
        File contents as a string, or None if the file cannot be read.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            logging.getLogger(__name__).error(f"File not found: {filepath}")
            return None
        if not path.is_file():
            logging.getLogger(__name__).error(f"Path is not a file: {filepath}")
            return None

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        logging.getLogger(__name__).info(f"Read file: {filepath} ({len(content)} characters)")
        return content

    except PermissionError:
        logging.getLogger(__name__).error(f"Permission denied reading file: {filepath}")
    except UnicodeDecodeError:
        logging.getLogger(__name__).error(f"File encoding error (not UTF-8): {filepath}")
    except OSError as e:
        logging.getLogger(__name__).error(f"OS error reading file: {e}")

    return None