"""
Fast web crawler with concurrent request handling

This module provides high-performance crawling using asyncio
and concurrent request processing.
"""

import asyncio
import aiohttp
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Callable, Tuple
from collections import deque
from dataclasses import dataclass
import time
import logging
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import concurrent.futures
from threading import Lock

from .crawler import CrawlResult, CrawlStats
from .parser import HTMLParser
from utils.rate_limiter import RateLimiter
from utils.exceptions import CrawlError, NetworkError

logger = logging.getLogger(__name__)


class FastCrawler:
    """
    High-performance web crawler using concurrent requests
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        rate_limiter: Optional[RateLimiter] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        keywords: Optional[List[str]] = None,
        min_delay: float = 0.1,  # Minimum delay between requests
        use_blocklist: bool = True
    ):
        """
        Initialize fast crawler
        
        Args:
            max_workers: Maximum concurrent workers
            rate_limiter: Rate limiter instance
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            keywords: Keywords to search for
            min_delay: Minimum delay between requests
            use_blocklist: Whether to use the blocked domains list
            min_delay: Minimum delay between requests (faster than default)
        """
        self.max_workers = max_workers
        self.rate_limiter = rate_limiter or RateLimiter(default_delay=min_delay)
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.keywords = [k.lower() for k in (keywords or [])]
        self.use_blocklist = use_blocklist
        
        # Thread-safe collections
        self.visited_urls: Set[str] = set()
        self.results: List[CrawlResult] = []
        self.queue: deque = deque()
        self.stats = CrawlStats()
        self._lock = Lock()
        
        # Store HTML responses for parsing
        self.html_cache: Dict[str, str] = {}
        
        # Domain request tracking for rate limiting
        self.domain_last_request: Dict[str, float] = {}
        
        # Load blocked domains
        self.blocked_domains: Set[str] = set()
        self.skip_extensions: Set[str] = set()
        if use_blocklist:
            self._load_blocked_domains()
    
    def _load_blocked_domains(self) -> None:
        """Load blocked domains from configuration file."""
        config_path = Path("config/blocked_domains.yaml")
        if not config_path.exists():
            logger.warning("Blocked domains configuration not found")
            return
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Collect all blocked domains
            for category in ['ad_networks', 'third_party', 'analytics', 'cdns', 
                           'social_widgets', 'marketing', 'video_players', 
                           'payment', 'other']:
                if category in config:
                    self.blocked_domains.update(config[category])
            
            # Load skip extensions
            if 'skip_extensions' in config:
                self.skip_extensions.update(config['skip_extensions'])
            
            logger.info(f"Loaded {len(self.blocked_domains)} blocked domains")
            
        except Exception as e:
            logger.error(f"Error loading blocked domains: {e}")
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison"""
        parsed = urlparse(url.lower())
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized
    
    def _should_crawl_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled"""
        try:
            parsed = urlparse(url)
            
            # Basic checks
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Check blocked domains
            if self.use_blocklist:
                # Check full domain and subdomains
                domain_parts = parsed.netloc.split('.')
                for i in range(len(domain_parts)):
                    check_domain = '.'.join(domain_parts[i:])
                    if check_domain in self.blocked_domains:
                        logger.debug(f"URL blocked by domain blocklist: {url}")
                        return False
            
            # Skip non-HTML resources
            path_lower = parsed.path.lower()
            
            # Use loaded skip extensions if available
            if self.skip_extensions:
                if any(path_lower.endswith(ext) for ext in self.skip_extensions):
                    return False
            else:
                # Fallback to default extensions
                skip_extensions = (
                    '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip',
                    '.mp4', '.mp3', '.css', '.js', '.ico', '.xml',
                    '.json', '.webp', '.svg', '.woff', '.woff2', '.ttf',
                    '.eot', '.otf', '.mov', '.avi', '.wmv', '.flv',
                    '.swf', '.exe', '.dmg', '.pkg', '.deb', '.rpm'
                )
                if any(path_lower.endswith(ext) for ext in skip_extensions):
                    return False
            
            # Skip CDN-style URLs that likely don't contain content
            cdn_patterns = [
                '/assets/', '/static/', '/dist/', '/build/',
                '/vendor/', '/lib/', '/modules/', '/bundles/',
                '/_next/', '/.well-known/', '/cdn-cgi/', '/wp-content/plugins/',
                '/wp-content/themes/', '/wp-includes/'
            ]
            if any(pattern in path_lower for pattern in cdn_patterns):
                logger.debug(f"URL appears to be CDN/asset: {url}")
                return False
            
            # Skip common tracking/ad/social URLs
            skip_patterns = [
                'utm_', 'fbclid=', 'gclid=', 'mc_', 'fb_', 'twitter.com',
                'facebook.com', 'google.com/ads', 'doubleclick.net',
                'googlesyndication.com', 'googletagmanager.com',
                'google-analytics.com', 'amazon-adsystem.com',
                '#', 'javascript:', 'mailto:', 'tel:', 'whatsapp:',
                'share', 'print', 'email', 'login', 'signin', 'register'
            ]
            
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in skip_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_links_fast(self, html: str, base_url: str) -> List[str]:
        """Fast link extraction using BeautifulSoup"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            links = []
            base_domain = urlparse(base_url).netloc
            
            for tag in soup.find_all(['a', 'link'], href=True):
                href = tag.get('href', '')
                if not href or href.startswith('#'):
                    continue
                
                absolute_url = urljoin(base_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                if (normalized_url not in self.visited_urls and 
                    self._should_crawl_url(normalized_url, base_domain)):
                    links.append(normalized_url)
            
            return links[:50]  # Limit links per page to avoid explosion
            
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
            return []
    
    def _check_keywords_fast(self, text: str) -> List[str]:
        """Fast keyword checking"""
        if not self.keywords:
            return []
        
        text_lower = text.lower()
        return [kw for kw in self.keywords if kw in text_lower]
    
    def _process_page(self, url: str, depth: int, fetch_func: Callable) -> Optional[CrawlResult]:
        """Process a single page"""
        result = CrawlResult(url=url, depth=depth)
        
        try:
            # Apply rate limiting per domain
            domain = urlparse(url).netloc
            wait_time = self.rate_limiter.wait_if_needed(domain)
            if wait_time > 0:
                logger.debug(f"Rate limited: waited {wait_time:.2f}s for {domain}")
            
            # Fetch page
            response = fetch_func(url)
            if not response or not response.text:
                raise NetworkError(f"Empty response from {url}")
            
            # Quick parse
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract text for keyword matching
            for script in soup(['script', 'style']):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            
            result.content = text[:2000]  # Limit content size
            result.title = soup.find('title').get_text(strip=True) if soup.find('title') else ''
            
            # Store HTML for later parsing
            with self._lock:
                self.html_cache[url] = response.text
            
            # Check keywords
            result.matched_keywords = self._check_keywords_fast(text)
            
            # Extract links for further crawling
            if depth < self.max_depth:
                result.links = self._extract_links_fast(response.text, url)
            
            with self._lock:
                self.stats.successful_pages += 1
                if result.matched_keywords:
                    self.stats.matched_pages += 1
            
            logger.debug(f"Processed: {url} (depth: {depth})")
            
        except Exception as e:
            result.error = str(e)
            with self._lock:
                self.stats.failed_pages += 1
            logger.debug(f"Failed: {url} - {e}")
        
        return result
    
    def crawl_concurrent(
        self,
        start_url: str,
        fetch_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[CrawlResult]:
        """
        Crawl website using concurrent workers
        
        Args:
            start_url: Starting URL
            fetch_func: Function to fetch page content
            progress_callback: Optional progress callback
            
        Returns:
            List of crawl results
        """
        # Reset state
        self.visited_urls.clear()
        self.results.clear()
        self.queue.clear()
        self.stats = CrawlStats()
        
        # Initialize queue
        start_url = self._normalize_url(start_url)
        self.queue.append((start_url, 0))
        
        # Process with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while (self.queue or futures) and len(self.results) < self.max_pages:
                # Submit new tasks
                while self.queue and len(futures) < self.max_workers:
                    url, depth = self.queue.popleft()
                    
                    with self._lock:
                        if url in self.visited_urls:
                            continue
                        self.visited_urls.add(url)
                        self.stats.total_pages += 1
                    
                    future = executor.submit(self._process_page, url, depth, fetch_func)
                    futures.append((future, url, depth))
                
                # Process completed futures
                if futures:
                    done_futures = []
                    for future_data in futures:
                        future, url, depth = future_data
                        if future.done():
                            done_futures.append(future_data)
                            
                            try:
                                result = future.result(timeout=0.1)
                                if result:
                                    self.results.append(result)
                                    
                                    # Update progress
                                    if progress_callback:
                                        progress_callback(
                                            len(self.results),
                                            self.max_pages,
                                            f"Crawled: {url[:50]}..."
                                        )
                                    
                                    # Add new URLs to queue
                                    if result.is_successful() and depth < self.max_depth:
                                        with self._lock:
                                            for link in result.links[:10]:  # Limit links per page
                                                if link not in self.visited_urls and len(self.queue) < 1000:
                                                    self.queue.append((link, depth + 1))
                                                    
                            except Exception as e:
                                logger.error(f"Error processing {url}: {e}")
                    
                    # Remove completed futures
                    for future_data in done_futures:
                        futures.remove(future_data)
                    
                    # Small delay to prevent CPU spinning
                    if not done_futures:
                        time.sleep(0.01)
        
        logger.info(
            f"Fast crawl completed: {self.stats.successful_pages} successful, "
            f"{self.stats.failed_pages} failed, {self.stats.matched_pages} matched"
        )
        
        return self.results


class AsyncFastCrawler:
    """
    Asynchronous fast crawler for maximum performance
    """
    
    def __init__(
        self,
        max_concurrent: int = 20,
        timeout: int = 10,
        keywords: Optional[List[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100
    ):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.keywords = [k.lower() for k in (keywords or [])]
        self.max_depth = max_depth
        self.max_pages = max_pages
        
        self.visited_urls: Set[str] = set()
        self.results: List[CrawlResult] = []
        self.queue: asyncio.Queue = asyncio.Queue()
        self.stats = CrawlStats()
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch page content asynchronously"""
        try:
            async with self._semaphore:
                async with session.get(url, timeout=self.timeout, ssl=False) as response:
                    if response.status == 200:
                        return await response.text()
                    return None
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None
    
    async def _process_page_async(
        self,
        session: aiohttp.ClientSession,
        url: str,
        depth: int
    ) -> Optional[CrawlResult]:
        """Process page asynchronously"""
        result = CrawlResult(url=url, depth=depth)
        
        try:
            html = await self._fetch_page(session, url)
            if not html:
                raise NetworkError(f"Failed to fetch {url}")
            
            # Parse in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def parse():
                soup = BeautifulSoup(html, 'lxml')
                for script in soup(['script', 'style']):
                    script.decompose()
                text = soup.get_text(separator=' ', strip=True)
                title = soup.find('title')
                return text, title.get_text(strip=True) if title else '', soup
            
            text, title, soup = await loop.run_in_executor(None, parse)
            
            result.content = text[:2000]
            result.title = title
            
            # Check keywords
            if self.keywords:
                text_lower = text.lower()
                result.matched_keywords = [kw for kw in self.keywords if kw in text_lower]
            
            # Extract links
            if depth < self.max_depth:
                def extract_links():
                    links = []
                    for tag in soup.find_all(['a'], href=True):
                        href = tag.get('href', '')
                        if href and not href.startswith('#'):
                            absolute_url = urljoin(url, href)
                            links.append(absolute_url)
                    return links[:30]
                
                result.links = await loop.run_in_executor(None, extract_links)
            
            self.stats.successful_pages += 1
            if result.matched_keywords:
                self.stats.matched_pages += 1
                
        except Exception as e:
            result.error = str(e)
            self.stats.failed_pages += 1
        
        return result
    
    async def crawl_async(
        self,
        start_url: str,
        progress_callback: Optional[Callable] = None
    ) -> List[CrawlResult]:
        """
        Crawl website asynchronously
        
        Args:
            start_url: Starting URL
            progress_callback: Optional progress callback
            
        Returns:
            List of crawl results
        """
        # Reset state
        self.visited_urls.clear()
        self.results.clear()
        self.stats = CrawlStats()
        
        # Create session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout
        ) as session:
            
            # Initialize queue
            await self.queue.put((start_url, 0))
            
            # Worker tasks
            workers = []
            for _ in range(min(self.max_concurrent, 10)):
                worker = asyncio.create_task(self._worker(session, progress_callback))
                workers.append(worker)
            
            # Wait for completion
            await self.queue.join()
            
            # Cancel workers
            for worker in workers:
                worker.cancel()
            
            await asyncio.gather(*workers, return_exceptions=True)
        
        return self.results
    
    async def _worker(self, session: aiohttp.ClientSession, progress_callback):
        """Worker to process URLs from queue"""
        while True:
            try:
                url, depth = await self.queue.get()
                
                if url in self.visited_urls or len(self.results) >= self.max_pages:
                    self.queue.task_done()
                    continue
                
                self.visited_urls.add(url)
                self.stats.total_pages += 1
                
                # Process page
                result = await self._process_page_async(session, url, depth)
                if result:
                    self.results.append(result)
                    
                    if progress_callback:
                        progress_callback(
                            len(self.results),
                            self.max_pages,
                            f"Crawling: {url[:50]}..."
                        )
                    
                    # Add new URLs
                    if result.is_successful() and depth < self.max_depth:
                        for link in result.links:
                            if link not in self.visited_urls:
                                await self.queue.put((link, depth + 1))
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                self.queue.task_done()