"""
Web crawler implementation for discovering and scraping related pages.
"""

import re
import yaml
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque
from typing import Set, List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
import time
import logging
from bs4 import BeautifulSoup

from core.validator import InputValidator
from utils.rate_limiter import RateLimiter
from utils.exceptions import CrawlError, NetworkError

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Container for crawl results from a single page."""
    url: str
    depth: int
    title: Optional[str] = None
    content: Optional[str] = None
    links: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def is_successful(self) -> bool:
        """Check if crawl was successful."""
        return self.error is None


@dataclass
class CrawlStats:
    """Statistics about the crawl operation."""
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    total_links_found: int = 0
    matched_pages: int = 0
    start_time: float = field(default_factory=time.time)
    
    @property
    def duration(self) -> float:
        """Get crawl duration in seconds."""
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Get percentage of successful crawls."""
        if self.total_pages == 0:
            return 0.0
        return (self.successful_pages / self.total_pages) * 100


class WebCrawler:
    """
    Web crawler for discovering and scraping pages based on keywords.
    """
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        max_depth: int = 3,
        max_pages: int = 100,
        allowed_domains: Optional[List[str]] = None,
        excluded_patterns: Optional[List[str]] = None,
        follow_external_links: bool = False,
        keywords: Optional[List[str]] = None,
        use_blocklist: bool = True
    ):
        """
        Initialize web crawler.
        
        Args:
            rate_limiter: Rate limiter instance
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            allowed_domains: List of allowed domains (None = same domain only)
            excluded_patterns: URL patterns to exclude (regex)
            follow_external_links: Whether to follow links to other domains
            keywords: Keywords to search for in pages
            use_blocklist: Whether to use the blocked domains list
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.allowed_domains = allowed_domains
        self.excluded_patterns = [re.compile(p) for p in (excluded_patterns or [])]
        self.follow_external_links = follow_external_links
        self.keywords = [k.lower() for k in (keywords or [])]
        self.use_blocklist = use_blocklist
        
        self.validator = InputValidator()
        self.visited_urls: Set[str] = set()
        self.queued_urls: deque = deque()
        self.results: List[CrawlResult] = []
        self.stats = CrawlStats()
        
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
        """Normalize URL for consistent comparison."""
        parsed = urlparse(url.lower())
        # Remove fragment and trailing slash
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled."""
        try:
            # Validate URL format
            if not self.validator.validate_url(url):
                return False
            
            parsed = urlparse(url)
            
            # Check scheme
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
            
            # Check excluded patterns
            for pattern in self.excluded_patterns:
                if pattern.search(url):
                    logger.debug(f"URL excluded by pattern: {url}")
                    return False
            
            # Check domain restrictions
            if not self.follow_external_links:
                if parsed.netloc != base_domain:
                    return False
            elif self.allowed_domains:
                if parsed.netloc not in self.allowed_domains:
                    return False
            
            # Skip common non-HTML resources and blocked extensions
            path_lower = parsed.path.lower()
            
            # Use loaded skip extensions if available
            if self.skip_extensions:
                if any(path_lower.endswith(ext) for ext in self.skip_extensions):
                    return False
            else:
                # Fallback to default extensions
                skip_extensions = (
                    '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip',
                    '.mp4', '.mp3', '.css', '.js', '.ico'
                )
                if any(path_lower.endswith(ext) for ext in skip_extensions):
                    return False
            
            # Skip CDN-style URLs that likely don't contain content
            cdn_patterns = [
                '/assets/', '/static/', '/dist/', '/build/',
                '/vendor/', '/lib/', '/modules/', '/bundles/',
                '/_next/', '/.well-known/', '/cdn-cgi/'
            ]
            if any(pattern in path_lower for pattern in cdn_patterns):
                logger.debug(f"URL appears to be CDN/asset: {url}")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error validating URL {url}: {e}")
            return False
    
    def _should_follow_url(self, url: str) -> bool:
        """Check if URL should be followed based on crawler rules."""
        parsed = urlparse(url)
        
        # Check if domain is allowed
        if self.allowed_domains is not None:
            if parsed.netloc not in self.allowed_domains:
                return False
        
        # Check excluded patterns
        for pattern in self.excluded_patterns:
            if pattern.search(url):
                return False
        
        # Check if external links are allowed
        if not self.follow_external_links:
            # Compare with start URL domain
            if hasattr(self, '_start_domain') and parsed.netloc != self._start_domain:
                return False
        
        return True
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all valid links from page."""
        links = []
        base_domain = urlparse(base_url).netloc
        
        # Store start domain if not set
        if not hasattr(self, '_start_domain'):
            self._start_domain = base_domain
        
        for tag in soup.find_all(['a', 'link']):
            href = tag.get('href')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(absolute_url)
            
            # Check if URL is valid and not visited
            if (normalized_url not in self.visited_urls and 
                self._is_valid_url(normalized_url, base_domain) and
                self._should_follow_url(normalized_url)):
                links.append(normalized_url)
        
        return links
    
    def _check_keywords(self, text: str) -> List[str]:
        """Check which keywords are present in text."""
        if not self.keywords:
            return []
        
        text_lower = text.lower()
        matched = []
        
        for keyword in self.keywords:
            if keyword in text_lower:
                matched.append(keyword)
        
        return matched
    
    def _extract_content(self, soup: BeautifulSoup) -> Tuple[str, Dict[str, Any]]:
        """Extract text content and metadata from page."""
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()
        
        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract metadata
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '')
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            metadata['keywords'] = meta_keywords.get('content', '')
        
        return text, metadata
    
    def crawl_page(self, url: str, depth: int, fetch_content_func: Callable) -> CrawlResult:
        """
        Crawl a single page.
        
        Args:
            url: URL to crawl
            depth: Current crawl depth
            fetch_content_func: Function to fetch page content
            
        Returns:
            CrawlResult object
        """
        result = CrawlResult(url=url, depth=depth)
        
        try:
            # Fetch page content
            response = fetch_content_func(url)
            if not response or not response.text:
                raise NetworkError(f"Empty response from {url}")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract content and metadata
            text, metadata = self._extract_content(soup)
            result.content = text[:5000]  # Limit content size
            result.metadata = metadata
            result.title = metadata.get('title', '')
            
            # Check keywords
            result.matched_keywords = self._check_keywords(text)
            
            # Extract links for further crawling
            if depth < self.max_depth:
                result.links = self._extract_links(soup, url)
                self.stats.total_links_found += len(result.links)
            
            if result.matched_keywords:
                self.stats.matched_pages += 1
            
            self.stats.successful_pages += 1
            logger.info(f"Successfully crawled: {url} (depth: {depth})")
            
        except Exception as e:
            result.error = str(e)
            self.stats.failed_pages += 1
            logger.error(f"Failed to crawl {url}: {e}")
        
        return result
    
    def crawl(
        self,
        start_url: str,
        fetch_content_func: Callable,
        progress_callback: Optional[Callable] = None
    ) -> List[CrawlResult]:
        """
        Start crawling from the given URL.
        
        Args:
            start_url: Starting URL
            fetch_content_func: Function to fetch page content
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of CrawlResult objects
        """
        # Reset state
        self.visited_urls.clear()
        self.queued_urls.clear()
        self.results.clear()
        self.stats = CrawlStats()
        
        # Normalize and validate start URL
        start_url = self._normalize_url(start_url)
        if not self.validator.validate_url(start_url):
            raise CrawlError(f"Invalid start URL: {start_url}")
        
        # Add start URL to queue
        self.queued_urls.append((start_url, 0))
        
        # Main crawl loop
        while self.queued_urls and len(self.results) < self.max_pages:
            url, depth = self.queued_urls.popleft()
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(url)
            self.stats.total_pages += 1
            
            # Update progress
            if progress_callback:
                progress_callback(
                    current=len(self.results),
                    total=self.max_pages,
                    message=f"Crawling: {url}"
                )
            
            # Rate limiting
            domain = urlparse(url).netloc
            self.rate_limiter.wait_if_needed(domain)
            
            # Crawl the page
            result = self.crawl_page(url, depth, fetch_content_func)
            self.results.append(result)
            
            # Add discovered links to queue
            if result.is_successful() and depth < self.max_depth:
                for link in result.links:
                    if link not in self.visited_urls:
                        self.queued_urls.append((link, depth + 1))
        
        logger.info(
            f"Crawl completed: {self.stats.successful_pages} successful, "
            f"{self.stats.failed_pages} failed, {self.stats.matched_pages} matched"
        )
        
        return self.results
    
    def get_matched_results(self) -> List[CrawlResult]:
        """Get only results that matched keywords."""
        return [r for r in self.results if r.matched_keywords]
    
    def get_stats(self) -> CrawlStats:
        """Get crawl statistics."""
        return self.stats
    
    def export_sitemap(self) -> Dict[str, Any]:
        """Export discovered site structure."""
        sitemap = {
            'start_url': self.results[0].url if self.results else None,
            'total_pages': len(self.results),
            'max_depth': self.max_depth,
            'pages': []
        }
        
        for result in self.results:
            page_info = {
                'url': result.url,
                'depth': result.depth,
                'title': result.title,
                'matched_keywords': result.matched_keywords,
                'links_count': len(result.links),
                'error': result.error
            }
            sitemap['pages'].append(page_info)
        
        return sitemap