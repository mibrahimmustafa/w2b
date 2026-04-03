"""
scraper.config
==============
Centralised runtime configuration for the W2B scraper.

All tuneable parameters live here so other modules never hard-code magic
values.  Import ``ScraperConfig`` and pass it around instead of individual
keyword arguments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Defaults (named constants — easier to grep and change in one place)
# ---------------------------------------------------------------------------
_DEFAULT_MAX_PAGES: int = 5
_DEFAULT_TIMEOUT: int = 25           # seconds — HTTP requests
_DEFAULT_REQUEST_DELAY: float = 1.5  # seconds — polite crawl delay
_DEFAULT_OUTPUT_DIR: Path = Path("scraped_results")

# Public — safe to import from other modules
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
DDG_SEARCH_URL: str = "https://html.duckduckgo.com/html/"


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------
@dataclass
class ScraperConfig:
    """
    Immutable-by-convention runtime configuration.

    Attributes:
        query:         Search phrase (required before running).
        max_pages:     Maximum DuckDuckGo result pages to fetch.
        output_dir:    Directory where all output files are written.
        timeout:       Per-request HTTP timeout in seconds.
        request_delay: Seconds to sleep between successive requests.
        user_agent:    User-Agent header sent with every HTTP request.
    """

    query: str = ""
    max_pages: int = _DEFAULT_MAX_PAGES
    output_dir: Path = field(default_factory=lambda: _DEFAULT_OUTPUT_DIR)
    timeout: int = _DEFAULT_TIMEOUT
    request_delay: float = _DEFAULT_REQUEST_DELAY
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        # Coerce str → Path in case the caller passed a plain string
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """
        Raise :class:`ValueError` if the config is not ready to use.

        Call this before starting any search/scrape pipeline.
        """
        if not self.query or not self.query.strip():
            raise ValueError("ScraperConfig.query must not be empty.")
        if self.max_pages < 1:
            raise ValueError("ScraperConfig.max_pages must be at least 1.")
        if self.timeout < 1:
            raise ValueError("ScraperConfig.timeout must be at least 1 second.")
        if self.request_delay < 0:
            raise ValueError("ScraperConfig.request_delay must be non-negative.")
