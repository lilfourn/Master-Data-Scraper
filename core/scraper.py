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
                 verify_ssl: bool = True):
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
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent or "MasterDataScraper/1.0"
        self.verify_ssl = verify_ssl
        self.cache_ttl = cache_ttl
        
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
            'retries': 0
        }
    
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
            'Upgrade-Insecure-Requests': '1'
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
        
        try:
            # Make the request
            start_time = time.time()
            response = self.session.request(method, url, **kwargs)
            elapsed = time.time() - start_time
            
            # Log request details
            logger.info(f"{method} {url} - Status: {response.status_code} - Time: {elapsed:.2f}s")
            
            # Detect and set proper encoding
            response.encoding = self._detect_encoding(response)
            
            # Raise for bad status codes
            response.raise_for_status()
            
            # Cache successful responses
            if use_cache and method.upper() == "GET" and response.status_code == 200:
                cache_key = self._get_cache_key(url, method, **kwargs)
                self._save_to_cache(cache_key, response)
            
            return response
            
        except requests.exceptions.RetryError as e:
            self.stats['retries'] += self.max_retries
            self.stats['errors'] += 1
            logger.error(f"Max retries exceeded for {url}: {str(e)}")
            raise
            
        except requests.exceptions.RequestException as e:
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
        
        return {
            **self.stats,
            'cache_size_memory': cache_size,
            'cache_size_disk': disk_cache_size,
            'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['requests_made'])
        }
    
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