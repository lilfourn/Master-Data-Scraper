"""
Base scraper module for web scraping functionality

This module provides the base scraper class with request handling,
session management, retry logic, and caching mechanisms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Tuple, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from functools import wraps
import logging
import chardet
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from core.crawler import WebCrawler, CrawlResult, CrawlStats
from urllib.parse import urlparse
from utils.human_behavior import HumanDelay, RequestScheduler, AdaptiveDelay
import asyncio
import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
import random

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers
    
    Provides common functionality for web scraping including:
    - Session management with connection pooling
    - Retry logic with exponential backoff
    - Request caching
    - Error handling
    - Rate limiting
    - Cookie and authentication support
    - Encoding detection
    """
    
    def __init__(self, 
                 timeout: int = 30,
                 max_retries: int = 3,
                 backoff_factor: float = 0.3,
                 user_agent: Optional[str] = None,
                 cache_dir: Optional[Path] = None,
                 cache_ttl: int = 3600,
                 verify_ssl: bool = True,
                 use_stealth: bool = True,
                 human_behavior: bool = True,
                 adaptive_delays: bool = True):
        """
        Initialize the base scraper
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for exponential retry delay
            user_agent: Custom user agent string
            cache_dir: Directory for caching responses
            cache_ttl: Cache time-to-live in seconds
            verify_ssl: Whether to verify SSL certificates
            use_stealth: Whether to use stealth features
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.verify_ssl = verify_ssl
        self.cache_ttl = cache_ttl
        self.use_stealth = use_stealth
        self.human_behavior = human_behavior
        self.adaptive_delays = adaptive_delays
        
        # Initialize stealth components if enabled
        if self.use_stealth:
            from utils.stealth import StealthSession
            self.stealth_session = StealthSession()
            self.user_agent = self.stealth_session.user_agent
        else:
            self.user_agent = user_agent or "MasterDataScraper/1.0"
        
        # Initialize human behavior simulation if enabled
        if self.human_behavior:
            self.human_delay = HumanDelay()
            self.request_scheduler = RequestScheduler()
        
        # Initialize adaptive delay if enabled
        if self.adaptive_delays:
            self.adaptive_delay = AdaptiveDelay(target_rps=0.5)  # 0.5 requests per second default
        
        # Initialize session with retry strategy
        self.session = self._create_session()
        
        # Cache for responses
        self._memory_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_dir = cache_dir or Path(".cache/responses")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Request statistics
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'retries': 0,
            'rate_limited': 0,
            'total_delay_time': 0.0
        }
        
        # Session tracking for better cookie/state management
        self._session_cookies = {}
        self._referer_chain = []  # Track referer chain for more realistic browsing
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and connection pooling"""
        session = requests.Session()
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False,
            respect_retry_after_header=True
        )
        
        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        
        # Mount adapter for both protocols
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        
        # Configure SSL verification
        session.verify = self.verify_ssl
        
        return session
    
    def _get_cache_key(self, url: str, method: str = "GET", **kwargs) -> str:
        """Generate a cache key for the request"""
        key_data = {
            'url': url,
            'method': method,
            'params': kwargs.get('params', {}),
            'headers': {k: v for k, v in kwargs.get('headers', {}).items() 
                       if k.lower() not in ['cookie', 'authorization']}
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[requests.Response]:
        """Get response from cache if valid"""
        # Check memory cache first
        if cache_key in self._memory_cache:
            response, cached_time = self._memory_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                self.stats['cache_hits'] += 1
                logger.debug(f"Memory cache hit for key {cache_key[:8]}")
                return response
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.cache"
        if cache_file.exists():
            try:
                cache_data = json.loads(cache_file.read_text())
                cached_time = datetime.fromisoformat(cache_data['cached_at'])
                
                if datetime.now() - cached_time < timedelta(seconds=self.cache_ttl):
                    # Reconstruct response
                    response = requests.Response()
                    response.status_code = cache_data['status_code']
                    response.headers = requests.structures.CaseInsensitiveDict(cache_data['headers'])
                    response._content = cache_data['content'].encode(cache_data['encoding'])
                    response.encoding = cache_data['encoding']
                    response.url = cache_data['url']
                    
                    self.stats['cache_hits'] += 1
                    logger.debug(f"Disk cache hit for key {cache_key[:8]}")
                    return response
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, response: requests.Response) -> None:
        """Save response to cache"""
        # Save to memory cache
        self._memory_cache[cache_key] = (response, datetime.now())
        
        # Save to disk cache
        try:
            cache_data = {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'encoding': response.encoding or 'utf-8',
                'cached_at': datetime.now().isoformat()
            }
            
            cache_file = self.cache_dir / f"{cache_key}.cache"
            cache_file.write_text(json.dumps(cache_data))
            logger.debug(f"Saved to cache: {cache_key[:8]}")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def _detect_encoding(self, response: requests.Response) -> str:
        """Detect response encoding using chardet"""
        if response.encoding:
            return response.encoding
        
        # Use chardet to detect encoding
        detected = chardet.detect(response.content)
        encoding = detected.get('encoding', 'utf-8')
        confidence = detected.get('confidence', 0)
        
        if confidence > 0.7:
            logger.debug(f"Detected encoding: {encoding} (confidence: {confidence})")
            return encoding
        
        # Fallback to utf-8
        return 'utf-8'
    
    def _apply_human_delay(self, url: str, response: Optional[requests.Response] = None) -> None:
        """Apply human-like delays between requests"""
        if not self.human_behavior:
            return
        
        # Get delay from request scheduler
        failed = response is not None and response.status_code >= 400
        delay = self.request_scheduler.get_next_request_time(failed=failed)
        
        # If adaptive delays are enabled, adjust based on server response time
        if self.adaptive_delays and response is not None:
            elapsed = response.elapsed.total_seconds()
            self.adaptive_delay.add_response_time(elapsed)
            adaptive_multiplier = self.adaptive_delay.get_delay() / 1.0
            delay *= adaptive_multiplier
        
        # Apply content-based delay if we have a response
        if response is not None and hasattr(response, 'text') and self.human_behavior:
            # Simulate reading time based on content length
            content_length = len(response.text)
            reading_delay = self.human_delay.get_page_reading_delay(content_length)
            delay += reading_delay * 0.3  # Don't add full reading time, just a portion
        
        # Track total delay time
        self.stats['total_delay_time'] += delay
        
        # Log delay info
        if delay > 5.0:
            logger.info(f"Applying {delay:.1f}s delay (simulating human behavior)")
        else:
            logger.debug(f"Applying {delay:.2f}s delay")
        
        time.sleep(delay)
    
    def _update_referer_chain(self, url: str) -> Optional[str]:
        """Update referer chain and return appropriate referer"""
        if not self._referer_chain:
            return None
        
        # Get the last URL as referer
        referer = self._referer_chain[-1]
        
        # Add current URL to chain
        self._referer_chain.append(url)
        
        # Keep only last 5 URLs in chain
        if len(self._referer_chain) > 5:
            self._referer_chain.pop(0)
        
        return referer
    
    def fetch(self, url: str, method: str = "GET", use_cache: bool = True, **kwargs) -> requests.Response:
        """
        Fetch a URL with error handling, caching, and encoding detection
        
        Args:
            url: The URL to fetch
            method: HTTP method (GET, POST, etc.)
            use_cache: Whether to use cache for this request
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object with proper encoding
            
        Raises:
            requests.RequestException: If the request fails after retries
        """
        self.stats['requests_made'] += 1
        
        # Check cache if enabled
        if use_cache and method.upper() == "GET":
            cache_key = self._get_cache_key(url, method, **kwargs)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Add timeout if not specified
        kwargs.setdefault('timeout', self.timeout)
        
        # Apply human delay before request (except for first request)
        if self.stats['requests_made'] > 0:
            self._apply_human_delay(url)
        
        # Use stealth headers if enabled
        if self.use_stealth:
            # Get referer from chain or use provided one
            referer = kwargs.get('headers', {}).get('Referer') or self._update_referer_chain(url)
            stealth_headers = self.stealth_session.get_headers(url, referer=referer)
            
            # Merge with any existing headers
            if 'headers' in kwargs:
                kwargs['headers'].update(stealth_headers)
            else:
                kwargs['headers'] = stealth_headers
            
            # Rotate user agent occasionally with some randomness
            if self.stats['requests_made'] > 0 and random.random() < 0.1:  # 10% chance
                self.stealth_session.rotate_user_agent()
                self.session.headers['User-Agent'] = self.stealth_session.user_agent
                logger.debug("Rotated user agent")
        
        # Manage cookies per domain for better session persistence
        domain = urlparse(url).netloc
        if domain in self._session_cookies:
            if 'cookies' in kwargs:
                kwargs['cookies'].update(self._session_cookies[domain])
            else:
                kwargs['cookies'] = self._session_cookies[domain]
        
        # Handle 429 errors with special retry logic
        max_429_retries = 3
        base_delay = 2.0  # Start with 2 seconds
        
        for attempt in range(max_429_retries + 1):
            try:
                # Make the request
                start_time = time.time()
                response = self.session.request(method, url, **kwargs)
                elapsed = time.time() - start_time
                
                # Log request details
                logger.info(f"{method} {url} - Status: {response.status_code} - Time: {elapsed:.2f}s")
                
                # Handle 429 specifically
                if response.status_code == 429:
                    self.stats['rate_limited'] += 1
                    if attempt < max_429_retries:
                        # Calculate exponential backoff with jitter
                        delay = base_delay * (2 ** attempt)
                        jitter = random.uniform(0.5, 1.5)
                        delay *= jitter
                        
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after) * 1.1)  # Add 10% buffer
                            except ValueError:
                                pass
                        
                        # If human behavior is enabled, add human-like variation
                        if self.human_behavior:
                            delay += random.uniform(5, 15)  # Human would wait a bit extra
                        
                        logger.warning(f"Rate limited (429) on {url}. Waiting {delay:.1f}s before retry {attempt + 1}/{max_429_retries}")
                        time.sleep(delay)
                        
                        # Rotate user agent after rate limit
                        if self.use_stealth:
                            self.stealth_session.rotate_user_agent()
                            self.session.headers['User-Agent'] = self.stealth_session.user_agent
                        
                        continue
                    else:
                        # Extract domain for the error message
                        domain = urlparse(url).netloc
                        raise requests.HTTPError(
                            f"Rate limit (429) persists after {max_429_retries} retries. "
                            f"Please increase the delay for {domain} in config/domains.yaml",
                            response=response
                        )
                
                # Detect and set proper encoding
                response.encoding = self._detect_encoding(response)
                
                # Raise for bad status codes (except 429 which we handle above)
                if response.status_code != 429:
                    response.raise_for_status()
                
                # Store cookies per domain
                if response.cookies:
                    domain = urlparse(url).netloc
                    if domain not in self._session_cookies:
                        self._session_cookies[domain] = {}
                    self._session_cookies[domain].update(response.cookies.get_dict())
                
                # Cache successful responses
                if use_cache and method.upper() == "GET" and response.status_code == 200:
                    cache_key = self._get_cache_key(url, method, **kwargs)
                    self._save_to_cache(cache_key, response)
                
                # Apply post-request delay based on response
                if self.human_behavior and response.status_code == 200:
                    self._apply_human_delay(url, response)
                
                return response
                
            except requests.exceptions.RetryError as e:
                self.stats['retries'] += self.max_retries
                self.stats['errors'] += 1
                logger.error(f"Max retries exceeded for {url}: {str(e)}")
                raise
                
            except requests.exceptions.RequestException as e:
                # Don't count 429 handling as regular errors
                if "429" not in str(e):
                    self.stats['errors'] += 1
                    logger.error(f"Error fetching {url}: {str(e)}")
                raise
    
    def clear_cache(self, memory_only: bool = False) -> int:
        """
        Clear the response cache
        
        Args:
            memory_only: If True, only clear memory cache, not disk cache
            
        Returns:
            Number of cache entries cleared
        """
        count = len(self._memory_cache)
        self._memory_cache.clear()
        
        if not memory_only:
            # Clear disk cache
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Error deleting cache file {cache_file}: {e}")
        
        logger.info(f"Cleared {count} cache entries")
        return count
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Set cookies for the session
        
        Args:
            cookies: Dictionary of cookie name-value pairs
        """
        self.session.cookies.update(cookies)
        logger.debug(f"Updated session cookies: {list(cookies.keys())}")
    
    def set_auth(self, auth: Union[Tuple[str, str], requests.auth.AuthBase]) -> None:
        """
        Set authentication for the session
        
        Args:
            auth: Tuple of (username, password) or requests auth object
        """
        self.session.auth = auth
        logger.debug("Session authentication configured")
    
    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        Update session headers
        
        Args:
            headers: Dictionary of headers to add/update
        """
        self.session.headers.update(headers)
        logger.debug(f"Updated session headers: {list(headers.keys())}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        cache_size = len(self._memory_cache)
        disk_cache_size = len(list(self.cache_dir.glob("*.cache")))
        
        stats = {
            **self.stats,
            'cache_size_memory': cache_size,
            'cache_size_disk': disk_cache_size,
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['requests_made']),
            'rate_limit_rate': self.stats['rate_limited'] / max(1, self.stats['requests_made']),
            'avg_delay_time': self.stats['total_delay_time'] / max(1, self.stats['requests_made'])
        }
        
        # Add human behavior stats if enabled
        if self.human_behavior:
            stats['session_duration'] = (datetime.now() - self.human_delay.session_start).total_seconds()
            stats['fatigue_level'] = self.human_delay.fatigue_level
        
        return stats
    
    @abstractmethod
    def scrape(self, url: str, element_type: str) -> Any:
        """
        Abstract method to scrape specific elements from a URL
        
        Args:
            url: The URL to scrape
            element_type: The type of HTML element to extract
            
        Returns:
            Scraped data in appropriate format
        """
        pass
    
    def close(self) -> None:
        """Close the session and clean up resources"""
        try:
            self.session.close()
            logger.debug("Session closed successfully")
        except Exception as e:
            logger.error(f"Error closing session: {e}")
        
        # Clear memory cache but keep disk cache
        self.clear_cache(memory_only=True)
        
        # Clear session data
        self._session_cookies.clear()
        self._referer_chain.clear()
    
    def crawl(
        self,
        start_url: str,
        keywords: Optional[List[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        allowed_domains: Optional[List[str]] = None,
        excluded_patterns: Optional[List[str]] = None,
        follow_external_links: bool = False,
        progress_callback: Optional[Any] = None
    ) -> Tuple[List[CrawlResult], CrawlStats]:
        """
        Crawl a website starting from the given URL
        
        Args:
            start_url: URL to start crawling from
            keywords: Keywords to search for in pages
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            allowed_domains: List of allowed domains
            excluded_patterns: URL patterns to exclude (regex)
            follow_external_links: Whether to follow external links
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (crawl results, crawl statistics)
        """
        from utils.rate_limiter import RateLimiter
        
        # Create crawler instance
        crawler = WebCrawler(
            rate_limiter=RateLimiter(),
            max_depth=max_depth,
            max_pages=max_pages,
            allowed_domains=allowed_domains,
            excluded_patterns=excluded_patterns,
            follow_external_links=follow_external_links,
            keywords=keywords
        )
        
        # Crawl the site
        results = crawler.crawl(
            start_url=start_url,
            fetch_content_func=self.fetch,
            progress_callback=progress_callback
        )
        
        stats = crawler.get_stats()
        
        # Log summary
        logger.info(
            f"Crawl completed: {stats.successful_pages} pages crawled, "
            f"{stats.matched_pages} pages matched keywords"
        )
        
        return results, stats
    
    def crawl_and_scrape(
        self,
        start_url: str,
        element_type: str,
        keywords: Optional[List[str]] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        **crawl_kwargs
    ) -> Dict[str, Any]:
        """
        Crawl a website and scrape specific elements from matched pages
        
        Args:
            start_url: URL to start crawling from
            element_type: Type of element to scrape from pages
            keywords: Keywords to search for
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            **crawl_kwargs: Additional crawl arguments
            
        Returns:
            Dictionary with crawl results and scraped data
        """
        # First crawl the site
        results, stats = self.crawl(
            start_url=start_url,
            keywords=keywords,
            max_depth=max_depth,
            max_pages=max_pages,
            **crawl_kwargs
        )
        
        # Get matched results
        matched_results = [r for r in results if r.matched_keywords] if keywords else results
        
        # Scrape data from matched pages
        scraped_data = []
        for result in matched_results:
            if result.is_successful():
                try:
                    data = self.scrape(result.url, element_type)
                    scraped_data.append({
                        'url': result.url,
                        'title': result.title,
                        'depth': result.depth,
                        'keywords': result.matched_keywords,
                        'data': data
                    })
                except Exception as e:
                    logger.error(f"Error scraping {result.url}: {e}")
        
        return {
            'crawl_stats': {
                'total_pages': stats.total_pages,
                'successful_pages': stats.successful_pages,
                'failed_pages': stats.failed_pages,
                'matched_pages': stats.matched_pages,
                'duration': stats.duration
            },
            'scraped_pages': len(scraped_data),
            'data': scraped_data
        }


class AsyncBaseScraper(BaseScraper):
    """
    Async version of BaseScraper for high-performance concurrent scraping
    
    Provides the same functionality as BaseScraper but with async/await support
    for better performance when scraping multiple URLs concurrently.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize async scraper with same parameters as BaseScraper"""
        super().__init__(*args, **kwargs)
        self._async_session = None
        self._connector = None
        
    async def _create_async_session(self) -> ClientSession:
        """Create an aiohttp session with proper configuration"""
        # Create connector with connection pooling
        self._connector = TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
            enable_cleanup_closed=True,
            force_close=True,
            ssl=self.verify_ssl
        )
        
        # Create timeout configuration
        timeout = ClientTimeout(
            total=self.timeout,
            connect=10,
            sock_connect=10,
            sock_read=self.timeout
        )
        
        # Create session with default headers
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers=headers,
            trust_env=True
        )
        
        return session
    
    async def _ensure_session(self) -> ClientSession:
        """Ensure async session exists and return it"""
        if self._async_session is None or self._async_session.closed:
            self._async_session = await self._create_async_session()
        return self._async_session
    
    async def _apply_human_delay_async(self, url: str, response: Optional[aiohttp.ClientResponse] = None) -> None:
        """Async version of human delay application"""
        if not self.human_behavior:
            return
        
        # Get delay from request scheduler
        failed = response is not None and response.status >= 400
        delay = self.request_scheduler.get_next_request_time(failed=failed)
        
        # If adaptive delays are enabled, adjust based on server response time
        if self.adaptive_delays and response is not None and hasattr(response, 'request_info'):
            elapsed = (response.request_info.headers_received - response.request_info.start).total_seconds()
            self.adaptive_delay.add_response_time(elapsed)
            adaptive_multiplier = self.adaptive_delay.get_delay() / 1.0
            delay *= adaptive_multiplier
        
        # Apply content-based delay if we have a response
        if response is not None and self.human_behavior:
            try:
                text = await response.text()
                content_length = len(text)
                reading_delay = self.human_delay.get_page_reading_delay(content_length)
                delay += reading_delay * 0.3
            except:
                pass
        
        # Track total delay time
        self.stats['total_delay_time'] += delay
        
        # Log delay info
        if delay > 5.0:
            logger.info(f"Applying {delay:.1f}s delay (simulating human behavior)")
        else:
            logger.debug(f"Applying {delay:.2f}s delay")
        
        await asyncio.sleep(delay)
    
    async def fetch_async(self, url: str, method: str = "GET", use_cache: bool = True, **kwargs) -> aiohttp.ClientResponse:
        """
        Async fetch with same features as sync version
        
        Args:
            url: URL to fetch
            method: HTTP method
            use_cache: Whether to use cache
            **kwargs: Additional arguments
            
        Returns:
            aiohttp ClientResponse
        """
        self.stats['requests_made'] += 1
        
        # Check cache if enabled
        if use_cache and method.upper() == "GET":
            cache_key = self._get_cache_key(url, method, **kwargs)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                # Convert to async-compatible response
                return cached_response
        
        # Apply human delay before request
        if self.stats['requests_made'] > 0:
            await self._apply_human_delay_async(url)
        
        # Ensure session exists
        session = await self._ensure_session()
        
        # Use stealth headers if enabled
        if self.use_stealth:
            referer = kwargs.get('headers', {}).get('Referer') or self._update_referer_chain(url)
            stealth_headers = self.stealth_session.get_headers(url, referer=referer)
            
            if 'headers' in kwargs:
                kwargs['headers'].update(stealth_headers)
            else:
                kwargs['headers'] = stealth_headers
            
            # Rotate user agent occasionally
            if self.stats['requests_made'] > 0 and random.random() < 0.1:
                self.stealth_session.rotate_user_agent()
                session.headers['User-Agent'] = self.stealth_session.user_agent
        
        # Handle retries with exponential backoff
        max_retries = self.max_retries
        base_delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                async with session.request(method, url, **kwargs) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        self.stats['rate_limited'] += 1
                        if attempt < max_retries:
                            delay = base_delay * (2 ** attempt) * random.uniform(0.5, 1.5)
                            retry_after = response.headers.get('Retry-After')
                            if retry_after:
                                try:
                                    delay = max(delay, float(retry_after) * 1.1)
                                except:
                                    pass
                            
                            if self.human_behavior:
                                delay += random.uniform(5, 15)
                            
                            logger.warning(f"Rate limited (429) on {url}. Waiting {delay:.1f}s")
                            await asyncio.sleep(delay)
                            
                            if self.use_stealth:
                                self.stealth_session.rotate_user_agent()
                                session.headers['User-Agent'] = self.stealth_session.user_agent
                            
                            continue
                        else:
                            domain = urlparse(url).netloc
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=429,
                                message=f"Rate limit persists for {domain}"
                            )
                    
                    # Read response content
                    content = await response.read()
                    text = await response.text()
                    
                    # Apply post-request delay
                    if self.human_behavior and response.status == 200:
                        await self._apply_human_delay_async(url, response)
                    
                    # Store in cache if successful
                    if use_cache and method.upper() == "GET" and response.status == 200:
                        # Create a mock requests.Response for caching
                        mock_response = requests.Response()
                        mock_response.status_code = response.status
                        mock_response.headers = dict(response.headers)
                        mock_response._content = content
                        mock_response.encoding = response.charset or 'utf-8'
                        mock_response.url = str(response.url)
                        
                        cache_key = self._get_cache_key(url, method, **kwargs)
                        self._save_to_cache(cache_key, mock_response)
                    
                    response.raise_for_status()
                    return response
                    
            except aiohttp.ClientError as e:
                if attempt < max_retries:
                    self.stats['retries'] += 1
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Error fetching {url}, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self.stats['errors'] += 1
                    logger.error(f"Error fetching {url}: {e}")
                    raise
    
    async def fetch_multiple(self, urls: List[str], method: str = "GET", 
                           max_concurrent: int = 10, **kwargs) -> List[Union[aiohttp.ClientResponse, Exception]]:
        """
        Fetch multiple URLs concurrently with rate limiting
        
        Args:
            urls: List of URLs to fetch
            method: HTTP method
            max_concurrent: Maximum concurrent requests
            **kwargs: Additional arguments for each request
            
        Returns:
            List of responses or exceptions
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> Union[aiohttp.ClientResponse, Exception]:
            async with semaphore:
                try:
                    return await self.fetch_async(url, method=method, **kwargs)
                except Exception as e:
                    return e
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def close_async(self) -> None:
        """Close async session and clean up resources"""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
        
        if self._connector and not self._connector.closed:
            await self._connector.close()
        
        # Give time for connections to close properly
        await asyncio.sleep(0.1)
        
        # Call parent close method
        super().close()
    
    @abstractmethod
    async def scrape_async(self, url: str, element_type: str) -> Any:
        """
        Abstract async method to scrape specific elements
        
        Args:
            url: URL to scrape
            element_type: Type of element to extract
            
        Returns:
            Scraped data
        """
        pass