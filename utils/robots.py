"""
Robots.txt compliance module for ethical web scraping

This module provides functionality to parse and respect robots.txt files
to ensure ethical scraping practices.
"""

from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Optional, Dict, Tuple
import logging
import requests
from functools import lru_cache
import time

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Handles robots.txt parsing and compliance checking
    """
    
    def __init__(self, user_agent: str = "MasterDataScraper/1.0", 
                 cache_size: int = 100,
                 cache_ttl: int = 86400):  # 24 hours
        """
        Initialize robots checker
        
        Args:
            user_agent: User agent string to check rules for
            cache_size: Maximum number of robots.txt files to cache
            cache_ttl: Cache time-to-live in seconds
        """
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[RobotFileParser, float]] = {}
        self._get_robots_txt = lru_cache(maxsize=cache_size)(self._get_robots_txt_uncached)
    
    def _get_robots_txt_uncached(self, domain: str) -> Optional[RobotFileParser]:
        """
        Fetch and parse robots.txt for a domain
        
        Args:
            domain: Domain to fetch robots.txt for
            
        Returns:
            RobotFileParser instance or None if not found
        """
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            # Check cache first
            if domain in self._cache:
                parser, cached_time = self._cache[domain]
                if time.time() - cached_time < self.cache_ttl:
                    return parser
            
            # Fetch robots.txt
            response = requests.get(robots_url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Parse robots.txt
                parser = RobotFileParser()
                parser.parse(response.text.splitlines())
                
                # Cache the parser
                self._cache[domain] = (parser, time.time())
                
                logger.debug(f"Successfully fetched robots.txt for {domain}")
                return parser
            elif response.status_code == 404:
                # No robots.txt means all allowed
                logger.debug(f"No robots.txt found for {domain} (404)")
                return None
            else:
                logger.warning(f"Unexpected status {response.status_code} for {robots_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching robots.txt for {domain}: {str(e)}")
            # In case of error, be conservative and assume restrictions
            return None
    
    def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
            user_agent: Optional user agent to check (defaults to instance user_agent)
            
        Returns:
            True if allowed, False if disallowed
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        if not domain:
            logger.warning(f"Invalid URL for robots check: {url}")
            return False
        
        # Get robots.txt parser
        parser = self._get_robots_txt(domain)
        
        if parser is None:
            # No robots.txt or error fetching - allow by default
            return True
        
        # Check if URL is allowed
        agent = user_agent or self.user_agent
        can_fetch = parser.can_fetch(agent, url)
        
        if not can_fetch:
            logger.info(f"Robots.txt disallows fetching {url} for user-agent {agent}")
        
        return can_fetch
    
    def get_crawl_delay(self, domain: str, user_agent: Optional[str] = None) -> Optional[float]:
        """
        Get crawl delay from robots.txt
        
        Args:
            domain: Domain to check
            user_agent: Optional user agent to check
            
        Returns:
            Crawl delay in seconds or None if not specified
        """
        parser = self._get_robots_txt(domain)
        
        if parser is None:
            return None
        
        agent = user_agent or self.user_agent
        
        # Try to get crawl delay
        # Note: robotparser doesn't have direct crawl-delay support,
        # so we'll parse it manually from the raw content
        if hasattr(parser, 'entries'):
            for entry in parser.entries:
                if entry.applies_to(agent):
                    # Look for crawl-delay in the entry
                    if hasattr(entry, 'delay'):
                        return entry.delay
        
        return None
    
    def get_sitemap_urls(self, domain: str) -> list[str]:
        """
        Extract sitemap URLs from robots.txt
        
        Args:
            domain: Domain to check
            
        Returns:
            List of sitemap URLs
        """
        robots_url = f"https://{domain}/robots.txt"
        sitemaps = []
        
        try:
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                for line in response.text.splitlines():
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemaps.append(sitemap_url)
        except Exception as e:
            logger.error(f"Error fetching sitemaps from robots.txt: {str(e)}")
        
        return sitemaps
    
    def check_url_batch(self, urls: list[str], user_agent: Optional[str] = None) -> Dict[str, bool]:
        """
        Check multiple URLs for robots.txt compliance
        
        Args:
            urls: List of URLs to check
            user_agent: Optional user agent to check
            
        Returns:
            Dictionary mapping URLs to allowed/disallowed status
        """
        results = {}
        
        for url in urls:
            results[url] = self.can_fetch(url, user_agent)
        
        return results
    
    def clear_cache(self) -> None:
        """Clear the robots.txt cache"""
        self._cache.clear()
        self._get_robots_txt.cache_clear()
        logger.info("Cleared robots.txt cache")


class RobotsCompliantScraper:
    """
    Wrapper to make any scraper robots.txt compliant
    """
    
    def __init__(self, scraper, robots_checker: Optional[RobotsChecker] = None):
        """
        Initialize robots-compliant scraper
        
        Args:
            scraper: Base scraper instance
            robots_checker: RobotsChecker instance
        """
        self.scraper = scraper
        self.robots_checker = robots_checker or RobotsChecker(
            user_agent=getattr(scraper, 'user_agent', 'MasterDataScraper/1.0')
        )
    
    def fetch(self, url: str, **kwargs):
        """
        Fetch URL with robots.txt compliance check
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for scraper.fetch
            
        Returns:
            Response from scraper.fetch
            
        Raises:
            PermissionError: If robots.txt disallows fetching
        """
        # Check robots.txt
        if not self.robots_checker.can_fetch(url):
            raise PermissionError(f"Robots.txt disallows fetching {url}")
        
        # Check for crawl delay
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        crawl_delay = self.robots_checker.get_crawl_delay(domain)
        if crawl_delay:
            # Apply crawl delay if specified
            import time
            time.sleep(crawl_delay)
        
        # Proceed with fetching
        return self.scraper.fetch(url, **kwargs)
    
    def __getattr__(self, name):
        """Delegate other attributes to the wrapped scraper"""
        return getattr(self.scraper, name)


# Utility functions
def create_robots_compliant_scraper(scraper_class, *args, **kwargs):
    """
    Factory function to create a robots-compliant scraper
    
    Args:
        scraper_class: Scraper class to instantiate
        *args, **kwargs: Arguments for scraper initialization
        
    Returns:
        RobotsCompliantScraper instance
    """
    base_scraper = scraper_class(*args, **kwargs)
    return RobotsCompliantScraper(base_scraper)


def check_robots_txt(url: str, user_agent: str = "MasterDataScraper/1.0") -> bool:
    """
    Quick check if a URL is allowed by robots.txt
    
    Args:
        url: URL to check
        user_agent: User agent string
        
    Returns:
        True if allowed, False if disallowed
    """
    checker = RobotsChecker(user_agent)
    return checker.can_fetch(url)