"""
scraper.deep_scraper
====================
Deep content extraction using Scrapling's stealth browser engine.

The :class:`DeepScraper` orchestrates a per-URL Playwright-based spider
that bypasses common bot-detection mechanisms.  It returns strongly-typed
``ScrapedPage`` dicts so callers never have to guess the shape of the data.

Usage::

    from scraper import DeepScraper, ScraperConfig

    config = ScraperConfig()
    scraper = DeepScraper(config)
    page = scraper.run("https://example.com")
    if page:
        print(page["metadata"]["title"])
"""

from __future__ import annotations

from typing import Optional, TypedDict

from scrapling.fetchers import AsyncStealthySession
from scrapling.spiders import Response, Spider

from .logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
class PageMetadata(TypedDict):
    """Basic metadata extracted from a scraped page."""

    url: str
    title: str
    description: str


class ScrapedPage(TypedDict):
    """Full result returned by :class:`DeepScraper.run`."""

    metadata: PageMetadata
    headings: dict[str, list[str]]
    paragraphs: list[str]
    links: list[str]


# ---------------------------------------------------------------------------
# Spider definition (module-level — no nested/dynamic class generation)
# ---------------------------------------------------------------------------
class _ContentSpider(Spider):
    """
    Stealth spider that extracts detailed content from a single URL,
    including metadata, headings, paragraphs, and links.
    """

    name = "w2b_content_spider"
    start_urls: list[str] = []

    # Minimum paragraph character length worth keeping
    _MIN_PARAGRAPH_LEN: int = 40
    # Maximum number of top paragraphs to retain
    _MAX_PARAGRAPHS: int = 50

    def configure_sessions(self, manager) -> None:  # type: ignore[override]
        manager.add(
            "stealth",
            AsyncStealthySession(headless=True, network_idle=True, timeout=60_000),
            default=True,
        )

    async def parse(self, response: Response):  # type: ignore[override]
        title = (response.css("title::text").get(default="") or "").strip()
        description = (response.css("meta[name='description']::attr(content)").get(default="") or "").strip()

        # Extract textual content with deeper xpath joining to handle nested tags like <a> or <span>
        def _get_clean_text(sel) -> str:
            return " ".join(t.strip() for t in sel.xpath(".//text()").getall() if t.strip())

        # Extract headings
        headings = {
            "h1": [ _get_clean_text(h) for h in response.css("h1") if _get_clean_text(h) ],
            "h2": [ _get_clean_text(h) for h in response.css("h2") if _get_clean_text(h) ],
            "h3": [ _get_clean_text(h) for h in response.css("h3") if _get_clean_text(h) ],
        }

        # Extract paragraphs (all combined nested text)
        all_paragraphs = []
        for p in response.css("p"):
            p_text = _get_clean_text(p)
            if len(p_text) >= self._MIN_PARAGRAPH_LEN:
                all_paragraphs.append(p_text)
        
        # Deduplicate while preserving order
        unique_paragraphs = list(dict.fromkeys(all_paragraphs))[:self._MAX_PARAGRAPHS]

        # Extract useful unique links on the page
        all_links = []
        for a in response.css("a::attr(href)").getall():
            link = a.strip()
            if link and not link.startswith(("javascript:", "mailto:", "tel:", "#")):
                if link not in all_links:
                    all_links.append(link)

        yield ScrapedPage(
            metadata=PageMetadata(url=response.url, title=title, description=description),
            headings=headings,
            paragraphs=unique_paragraphs,
            links=all_links[:100],  # Limit to top 100 links
        )


# ---------------------------------------------------------------------------
# DeepScraper
# ---------------------------------------------------------------------------
class DeepScraper:
    """
    Orchestrates stealth scraping of individual pages.

    Args:
        config: Optional scraper config (reserved for future per-page tuning).
    """

    def __init__(self) -> None:
        pass  # config injection ready for future extension

    def run(self, url: str) -> Optional[ScrapedPage]:
        """
        Scrape *url* and return the extracted content.

        Args:
            url: Fully-qualified URL to scrape.

        Returns:
            A :class:`ScrapedPage` dict on success, or ``None`` if the
            page could not be fetched or no items were yielded.
        """
        logger.debug("Starting deep scrape: %s", url)
        try:
            # Assign URL at class level so the Spider framework picks it up
            _ContentSpider.start_urls = [url]
            spider = _ContentSpider()
            result = spider.start()

            if not result.items:
                logger.warning("No items extracted from: %s", url)
                return None

            page: ScrapedPage = result.items[0]
            logger.debug(
                "Scraped '%s' — %d paragraph(s).",
                page["metadata"].get("title", url),
                len(page["paragraphs"]),
            )
            return page

        except Exception as exc:  # noqa: BLE001 — broad catch is intentional
            logger.error("Deep-scrape failed for '%s': %s", url, exc)
            return None
