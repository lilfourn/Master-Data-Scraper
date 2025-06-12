"""
Async scraper implementation using aiohttp

This module provides asynchronous web scraping capabilities
for improved performance with concurrent requests.
"""

import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from typing import List, Dict, Any, Optional, Set, Callable
import logging
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import chardet

from .scraper import BaseScraper
from .parser import HTMLParser
from .crawler import WebCrawler, CrawlResult
from utils.rate_limiter import AsyncRateLimiter
from utils.exceptions import NetworkError

logger = logging.getLogger(__name__)


class AsyncWebScraper(BaseScraper):
    """
    Asynchronous web scraper for high-performance scraping
    
    Uses aiohttp for concurrent HTTP requests and async/await patterns
    for improved performance when scraping multiple pages.
    """
    
    def __init__(self, 
                 max_concurrent_requests: int = 10,
                 timeout: int = 30,
                 **kwargs):
        """
        Initialize async scraper
        
        Args:
            max_concurrent_requests: Maximum concurrent requests
            timeout: Request timeout in seconds
            **kwargs: Additional arguments for BaseScraper
        """
        super().__init__(timeout=timeout, **kwargs)
        
        self.max_concurrent_requests = max_concurrent_requests
        self.session: Optional[ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Async rate limiter
        self.async_rate_limiter = AsyncRateLimiter()
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()
    
    async def start_session(self) -> None:
        """Start aiohttp session"""
        if self.session is None:
            timeout = ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=self.max_concurrent_requests,
                limit_per_host=5
            )
            
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            self.session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
            logger.debug("Async session started")
    
    async def close_session(self) -> None:
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("Async session closed")
    
    async def fetch_async(self, url: str, use_cache: bool = True) -> str:
        """
        Fetch URL asynchronously
        
        Args:
            url: URL to fetch
            use_cache: Whether to use cache
            
        Returns:
            Response text
        """
        # Check cache if enabled
        if use_cache:
            cache_key = self._get_cache_key(url, "GET")
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response.text
        
        # Apply rate limiting
        domain = urlparse(url).netloc
        await self.async_rate_limiter.wait_if_needed(domain)
        
        # Fetch with semaphore to limit concurrent requests
        async with self._semaphore:
            try:
                if not self.session:
                    await self.start_session()
                
                self.stats['requests_made'] += 1
                
                async with self.session.get(url, ssl=self.verify_ssl) as response:
                    response.raise_for_status()
                    
                    # Read content
                    content = await response.read()
                    
                    # Detect encoding
                    encoding = response.charset
                    if not encoding:
                        detected = chardet.detect(content)
                        encoding = detected.get('encoding', 'utf-8')
                    
                    text = content.decode(encoding, errors='replace')
                    
                    # Cache successful responses
                    if use_cache and response.status == 200:
                        # Create a mock requests.Response for caching
                        import requests
                        mock_response = requests.Response()
                        mock_response.status_code = response.status
                        mock_response._content = content
                        mock_response.encoding = encoding
                        mock_response.url = str(response.url)
                        mock_response.headers = dict(response.headers)
                        
                        self._save_to_cache(cache_key, mock_response)
                    
                    logger.info(f"Async GET {url} - Status: {response.status}")
                    return text
                    
            except aiohttp.ClientError as e:
                self.stats['errors'] += 1
                logger.error(f"Async request failed for {url}: {e}")
                raise NetworkError(f"Failed to fetch {url}: {str(e)}", url=url)
    
    async def scrape_async(self, url: str, element_type: str) -> Any:
        """
        Scrape URL asynchronously
        
        Args:
            url: URL to scrape
            element_type: Element type to extract
            
        Returns:
            Scraped data
        """
        # Fetch page content
        html_content = await self.fetch_async(url)
        
        # Parse HTML (synchronous operation)
        parser = HTMLParser(html_content)
        data = parser.parse(element_type)
        
        return data
    
    async def scrape_multiple_async(self, urls: List[str], element_type: str) -> Dict[str, Any]:
        """
        Scrape multiple URLs concurrently
        
        Args:
            urls: List of URLs to scrape
            element_type: Element type to extract
            
        Returns:
            Dictionary mapping URLs to results
        """
        tasks = []
        for url in urls:
            task = self._scrape_with_error_handling(url, element_type)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        return dict(zip(urls, results))
    
    async def _scrape_with_error_handling(self, url: str, element_type: str) -> Dict[str, Any]:
        """Scrape with error handling"""
        try:
            data = await self.scrape_async(url, element_type)
            return {
                'success': True,
                'data': data,
                'element_count': self._count_elements(data)
            }
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _count_elements(self, data: Any) -> int:
        """Count elements in data"""
        if isinstance(data, list):
            return len(data)
        elif hasattr(data, 'shape'):
            return data.shape[0]
        return 1
    
    # Override base scraper method to use async
    def scrape(self, url: str, element_type: str) -> Any:
        """
        Synchronous wrapper for async scraping
        
        Args:
            url: URL to scrape
            element_type: Element type to extract
            
        Returns:
            Scraped data
        """
        # Run async function in event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.scrape_async(url, element_type))
    
    async def crawl_async(
        self,
        start_url: str,
        keywords: Optional[List[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        progress_callback: Optional[Callable] = None
    ) -> List[CrawlResult]:
        """
        Crawl website asynchronously
        
        Args:
            start_url: Starting URL
            keywords: Keywords to search for
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            progress_callback: Progress callback function
            
        Returns:
            List of crawl results
        """
        crawler = WebCrawler(
            rate_limiter=self.async_rate_limiter,
            max_depth=max_depth,
            max_pages=max_pages,
            keywords=keywords
        )
        
        # Use async fetch function
        async def async_fetch_wrapper(url: str):
            """Wrapper to make fetch compatible with crawler"""
            text = await self.fetch_async(url)
            # Create mock response
            import requests
            response = requests.Response()
            response._content = text.encode('utf-8')
            response.encoding = 'utf-8'
            response.status_code = 200
            response.url = url
            return response
        
        # Note: The crawler itself is not async, but uses our async fetch
        # For a fully async crawler, we would need to rewrite the crawler class
        results = []
        visited = set()
        queue = [(start_url, 0)]
        
        while queue and len(results) < max_pages:
            url, depth = queue.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            if progress_callback:
                progress_callback(len(results), max_pages, f"Crawling: {url}")
            
            try:
                response = await async_fetch_wrapper(url)
                result = crawler.crawl_page(url, depth, lambda u: response)
                results.append(result)
                
                # Add new URLs to queue
                if result.is_successful() and depth < max_depth:
                    for link in result.links:
                        if link not in visited:
                            queue.append((link, depth + 1))
                            
            except Exception as e:
                logger.error(f"Failed to crawl {url}: {e}")
        
        return results


class AsyncRateLimiter:
    """Simple async rate limiter"""
    
    def __init__(self, default_delay: float = 1.0):
        self.default_delay = default_delay
        self.last_request_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self, domain: str) -> float:
        """Wait if needed to respect rate limits"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            last_time = self.last_request_time.get(domain, 0)
            
            time_since_last = now - last_time
            if time_since_last < self.default_delay:
                wait_time = self.default_delay - time_since_last
                await asyncio.sleep(wait_time)
                self.last_request_time[domain] = now + wait_time
                return wait_time
            else:
                self.last_request_time[domain] = now
                return 0.0


# Convenience function for async scraping
async def scrape_urls_async(urls: List[str], element_type: str = "table", 
                           max_concurrent: int = 10) -> Dict[str, Any]:
    """
    Convenience function to scrape multiple URLs asynchronously
    
    Args:
        urls: List of URLs to scrape
        element_type: Element type to extract
        max_concurrent: Maximum concurrent requests
        
    Returns:
        Dictionary of results
    """
    async with AsyncWebScraper(max_concurrent_requests=max_concurrent) as scraper:
        results = await scraper.scrape_multiple_async(urls, element_type)
    
    return results