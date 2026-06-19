"""
main.py
-------
Entry point for the Blog Summarizer application.

Supports two input modes:
1. URL mode:  python main.py --url https://example.com/blog
2. File mode: python main.py --file path/to/article.txt

Usage:
    python src/main.py --url <blog_url>
    python src/main.py --file <text_file_path>
    python src/main.py --url <blog_url> --output custom_name.txt
"""

import argparse
import sys
import logging
from pathlib import Path

# Add the src/ directory to the path so relative imports work cleanly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

from scraper import scrape_blog
from summarizer import generate_summary
from utils import (
    configure_logging,
    count_words,
    count_sentences,
    save_summary,
    read_text_file,
    validate_summary,
)

# Load environment variables from .env file (GEMINI_API_KEY, etc.)
load_dotenv()

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        prog="blog-summarizer",
        description=(
            "AI-powered Blog Summarizer — generates a concise summary "
            "(≤300 words, ≤20 sentences) from a blog URL or text file "
            "using Google Gemini."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Input source: URL or local file (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--url",
        type=str,
        metavar="URL",
        help="Full URL of the blog/article to summarize.\nExample: --url https://example.com/blog",
    )
    input_group.add_argument(
        "--file",
        type=str,
        metavar="FILE",
        help="Path to a plain text file containing the article.\nExample: --file article.txt",
    )

    # Optional: custom output filename
    parser.add_argument(
        "--output",
        type=str,
        default="generated_summary.txt",
        metavar="FILENAME",
        help="Output filename for the summary (default: generated_summary.txt)",
    )

    # Optional: verbose debug logging
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    return parser.parse_args()


def display_summary(summary: str) -> None:
    """
    Display the generated summary in the terminal with formatting.

    Args:
        summary: The summary text to display.
    """
    validation = validate_summary(summary)
    word_count = validation["word_count"]
    sentence_count = validation["sentence_count"]
    status = "✅ WITHIN LIMITS" if validation["valid"] else "⚠️  EXCEEDS LIMITS"

    separator = "─" * 65
    print(f"\n{separator}")
    print("  📝  GENERATED BLOG SUMMARY")
    print(separator)
    print(f"\n{summary}\n")
    print(separator)
    print(f"  Words:     {word_count} / 300")
    print(f"  Sentences: {sentence_count} / 20")
    print(f"  Status:    {status}")
    print(f"{separator}\n")


def run() -> int:
    """
    Main application workflow.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    args = parse_arguments()

    # Configure logging based on verbosity flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(level=log_level)

    logger.info("=" * 50)
    logger.info("Blog Summarizer — Starting")
    logger.info("=" * 50)

    article_text: str | None = None

    # ── Input: URL mode ─────────────────────────────────────────────────────
    if args.url:
        logger.info(f"Mode: URL | Target: {args.url}")
        article_text = scrape_blog(args.url)

        if article_text is None:
            print(
                "\n❌ Error: Failed to retrieve article from the URL.\n"
                "   Possible causes:\n"
                "   • Invalid or unreachable URL\n"
                "   • Network connectivity issue\n"
                "   • Website blocking scraping requests\n"
                "\n   Try saving the article text to a file and use --file mode."
            )
            return 1

    # ── Input: File mode ─────────────────────────────────────────────────────
    elif args.file:
        logger.info(f"Mode: File | Path: {args.file}")
        article_text = read_text_file(args.file)

        if article_text is None:
            print(
                f"\n❌ Error: Could not read file '{args.file}'.\n"
                "   Please check that the file exists and is readable."
            )
            return 1

    # ── Guard: Empty content ─────────────────────────────────────────────────
    if not article_text or not article_text.strip():
        print("\n❌ Error: The article content is empty. Nothing to summarize.")
        return 1

    logger.info(f"Article retrieved: {len(article_text)} characters.")

    # ── Generate Summary ─────────────────────────────────────────────────────
    print("\n⏳ Generating summary using Groq ... please wait.\n")
    summary = generate_summary(article_text)

    if summary is None:
        print(
            "\n❌ Error: Summary generation failed.\n"
            "   Possible causes:\n"
            "   • GEMINI_API_KEY is missing or invalid\n"
            "   • Gemini API rate limit exceeded\n"
            "   • Network error during API call\n"
            "\n   Check logs above for details."
        )
        return 1

    # ── Display Summary ──────────────────────────────────────────────────────
    display_summary(summary)

    # ── Save Summary ─────────────────────────────────────────────────────────
    output_path = save_summary(summary, filename=args.output)
    print(f"💾 Summary saved to: {output_path}\n")

    logger.info("Blog Summarizer — Completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(run())