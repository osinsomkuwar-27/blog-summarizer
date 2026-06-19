"""
test_summarizer.py
------------------
Unit tests for the Blog Summarizer project.

Tests cover:
- URL validation
- Empty input handling
- Summary length validation
- Text cleaning
- Short article detection
- Word and sentence counting

Run with: pytest tests/test_summarizer.py -v
"""

import sys
from pathlib import Path

import pytest

# Add src/ to path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from scraper import is_valid_url
from utils import (
    clean_text,
    count_words,
    count_sentences,
    is_short_article,
    truncate_text,
    validate_summary,
    MAX_WORDS,
    MAX_SENTENCES,
)


# ═══════════════════════════════════════════════════════════════════════════════
# URL Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestURLValidation:
    """Tests for the is_valid_url() function."""

    def test_valid_http_url(self):
        """Standard HTTP URL should be valid."""
        assert is_valid_url("http://example.com") is True

    def test_valid_https_url(self):
        """Standard HTTPS URL should be valid."""
        assert is_valid_url("https://www.langchain.com/blog/langsmith-cli-skills") is True

    def test_valid_url_with_path(self):
        """URL with deep path should be valid."""
        assert is_valid_url("https://openai.com/blog/gpt-4-research") is True

    def test_valid_url_with_query_params(self):
        """URL with query parameters should be valid."""
        assert is_valid_url("https://example.com/search?q=python&page=2") is True

    def test_invalid_url_no_schema(self):
        """URL without http/https schema should be invalid."""
        assert is_valid_url("www.example.com") is False

    def test_invalid_url_empty_string(self):
        """Empty string should be invalid."""
        assert is_valid_url("") is False

    def test_invalid_url_ftp_schema(self):
        """FTP URL should be invalid (we only handle http/https)."""
        assert is_valid_url("ftp://example.com") is False

    def test_invalid_url_just_text(self):
        """Plain text is not a URL."""
        assert is_valid_url("not a url at all") is False

    def test_invalid_url_missing_domain(self):
        """URL with only schema and no domain should be invalid."""
        assert is_valid_url("https://") is False

    def test_invalid_url_spaces(self):
        """URL with spaces should be invalid."""
        assert is_valid_url("https://example .com/path") is False


# ═══════════════════════════════════════════════════════════════════════════════
# Empty Input Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmptyInput:
    """Tests for handling empty and whitespace-only input."""

    def test_clean_empty_string(self):
        """Cleaning empty string should return empty string."""
        assert clean_text("") == ""

    def test_clean_whitespace_only(self):
        """Cleaning whitespace-only string should return empty string."""
        assert clean_text("   \n\t  ") == ""

    def test_count_words_empty(self):
        """Word count of empty string should be 0."""
        assert count_words("") == 0

    def test_count_words_whitespace(self):
        """Word count of whitespace-only string should be 0."""
        assert count_words("   ") == 0

    def test_count_sentences_empty(self):
        """Sentence count of empty string should be 0."""
        assert count_sentences("") == 0

    def test_is_short_article_empty(self):
        """Empty string should be classified as a short article."""
        assert is_short_article("") is True

    def test_validate_summary_empty(self):
        """Empty summary should have 0 words and 0 sentences."""
        result = validate_summary("")
        assert result["word_count"] == 0
        assert result["sentence_count"] == 0
        # Empty is technically "valid" (it doesn't exceed limits)
        # but main.py handles empty output separately
        assert result["valid"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Summary Length Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryLengthValidation:
    """Tests for summary constraint enforcement."""

    def test_valid_summary_under_limits(self):
        """A short summary should pass validation."""
        summary = "This is a short summary. It has two sentences."
        result = validate_summary(summary)
        assert result["valid"] is True
        assert result["word_count"] <= MAX_WORDS
        assert result["sentence_count"] <= MAX_SENTENCES

    def test_summary_exactly_at_word_limit(self):
        """Summary with exactly 300 words should be valid."""
        summary = " ".join(["word"] * 300)
        result = validate_summary(summary)
        assert result["word_count"] == 300
        assert result["valid"] is True  # 300 == MAX_WORDS, not over

    def test_summary_exceeds_word_limit(self):
        """Summary with 301+ words should fail validation."""
        summary = " ".join(["word"] * 301)
        result = validate_summary(summary)
        assert result["valid"] is False
        assert any("word" in issue.lower() for issue in result["issues"])

    def test_summary_exceeds_sentence_limit(self):
        """Summary with 21+ sentences should fail validation."""
        # Build 21 proper sentences
        sentences = ["This is sentence number {}.".format(i) for i in range(21)]
        summary = " ".join(sentences)
        result = validate_summary(summary)
        assert result["valid"] is False
        assert any("sentence" in issue.lower() for issue in result["issues"])

    def test_summary_exactly_at_sentence_limit(self):
        """Summary with exactly 20 sentences should be valid."""
        sentences = ["This is sentence {}.".format(i) for i in range(20)]
        summary = " ".join(sentences)
        result = validate_summary(summary)
        assert result["sentence_count"] == 20
        assert result["valid"] is True

    def test_word_count_accurate(self):
        """Word count should match the actual number of words."""
        text = "The quick brown fox jumps over the lazy dog"
        assert count_words(text) == 9

    def test_sentence_count_accurate(self):
        """Sentence count should correctly count period-separated sentences."""
        text = "First sentence. Second sentence. Third sentence."
        assert count_sentences(text) == 3

    def test_sentence_count_mixed_punctuation(self):
        """Sentence counter should handle '!', '?', and '.' correctly."""
        text = "Is this working? Yes! It seems to be. Great."
        assert count_sentences(text) == 4


# ═══════════════════════════════════════════════════════════════════════════════
# Text Cleaning Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTextCleaning:
    """Tests for the clean_text() preprocessing function."""

    def test_clean_newlines(self):
        """Newlines should be converted to spaces."""
        assert clean_text("Hello\nWorld") == "Hello World"

    def test_clean_multiple_spaces(self):
        """Multiple consecutive spaces should be collapsed."""
        assert clean_text("Hello   World") == "Hello World"

    def test_clean_tabs(self):
        """Tabs should be replaced with spaces."""
        assert clean_text("Hello\tWorld") == "Hello World"

    def test_clean_mixed_whitespace(self):
        """Mixed whitespace should be normalized."""
        result = clean_text("Hello \n\t  World")
        assert result == "Hello World"

    def test_clean_strips_leading_trailing(self):
        """Leading and trailing whitespace should be stripped."""
        assert clean_text("  hello world  ") == "hello world"

    def test_clean_preserves_content(self):
        """Cleaning should not alter meaningful text content."""
        text = "LangSmith CLI provides agent-native workflows and skills."
        assert clean_text(text) == text


# ═══════════════════════════════════════════════════════════════════════════════
# Truncation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTruncation:
    """Tests for the truncate_text() function."""

    def test_no_truncation_short_text(self):
        """Text within limit should not be truncated."""
        text = "Short text."
        assert truncate_text(text, max_chars=1000) == text

    def test_truncation_at_word_boundary(self):
        """Truncation should occur at a word boundary, not mid-word."""
        text = "word " * 100  # 500 chars
        result = truncate_text(text, max_chars=50)
        assert len(result) <= 50
        # Should not end with a partial word
        assert not result.endswith("wor")
        assert result.split()[-1] == "word"

    def test_truncation_reduces_length(self):
        """Truncated text must be shorter than the original."""
        text = "a" * 20000
        result = truncate_text(text, max_chars=100)
        assert len(result) <= 100


# ═══════════════════════════════════════════════════════════════════════════════
# Short Article Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestShortArticleDetection:
    """Tests for the is_short_article() function."""

    def test_very_short_article(self):
        """A 10-word article should be flagged as short."""
        text = " ".join(["word"] * 10)
        assert is_short_article(text) is True

    def test_article_at_threshold(self):
        """An article at exactly the threshold should be flagged."""
        text = " ".join(["word"] * 150)
        assert is_short_article(text) is True

    def test_article_above_threshold(self):
        """An article above the threshold should not be flagged."""
        text = " ".join(["word"] * 200)
        assert is_short_article(text) is False

    def test_long_article_not_short(self):
        """A 1000-word article should never be flagged as short."""
        text = " ".join(["word"] * 1000)
        assert is_short_article(text) is False