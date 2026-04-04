"""
app.services.scraper_service
============================
Service layer for the W2B scraper. Integrates search and deep scraping
as a unified interface for the API and frontend.
"""

from __future__ import annotations
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from scraper import ScraperConfig, SearchEngine, DeepScraper, ScrapedPage, SearchResult
from scraper.logger import get_logger

logger = get_logger(__name__)

class ScraperService:
    """Handles high-level scraping operations asynchronously."""

    def __init__(self, output_dir: str = "scraped_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.deep_scraper = DeepScraper()

    async def search(self, query: str, max_pages: int = 5) -> List[SearchResult]:
        """Run DuckDuckGo discovery phase."""
        config = ScraperConfig(query=query, max_pages=max_pages, output_dir=self.output_dir)
        config.validate()
        
        # Offload the synchronous search to a thread to keep the API responsive
        engine = SearchEngine(config)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, engine.execute_search)
        return results

    async def scrape_url(self, url: str) -> Optional[ScrapedPage]:
        """Deep scrape a single URL asynchronously."""
        loop = asyncio.get_event_loop()
        # Offload logic that creates its own asyncio loop to a thread
        results = await loop.run_in_executor(None, self.deep_scraper.run, [url])
        return results[0] if results else None

    async def run_pipeline(self, query: str, max_pages: int = 2) -> Dict[str, Any]:
        """Full search-and-deep-scrape pipeline."""
        config = ScraperConfig(query=query, max_pages=max_pages)
        config.validate()

        logger.info("Starting pipeline in: %s", config.output_dir)

        discovered = await self.search(query, max_pages=max_pages)
        if not discovered:
            return {"count": 0, "results": [], "storage_path": str(config.output_dir)}

        # Phase 2: Batch Scrape
        urls = [item["url"] for item in discovered]
        loop = asyncio.get_event_loop()
        scraped_results = await loop.run_in_executor(None, self.deep_scraper.run, urls)
        
        scraped_pages = []
        from scraper.exporters import save_json
        
        for page in scraped_results:
            url = page["metadata"]["url"]
            file_path = config.output_dir / self._sanitize_filename(url)
            save_json(page, file_path)
            scraped_pages.append(page)
        
        return {
            "count": len(scraped_pages),
            "results": scraped_pages,
            "storage_path": str(config.output_dir)
        }

    def _sanitize_filename(self, url: str) -> str:
        """Safe filename from URL."""
        name = re.sub(r"https?://", "", url)
        name = re.sub(r"[^\w.\-]", "_", name)
        return f"{name[:100]}.json"
