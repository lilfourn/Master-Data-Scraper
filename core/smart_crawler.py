"""
Smart Web Crawler - Enhanced crawler with relevance-based link following

This module extends the basic crawler with intelligent link selection based on
content relevance, ensuring the crawler stays focused on related content.
"""

import logging
from typing import Set, List, Dict, Any, Optional, Callable, Tuple
from urllib.parse import urljoin, urlparse
from collections import deque
from dataclasses import dataclass, field
import time
import requests

from bs4 import BeautifulSoup

from .crawler import WebCrawler, CrawlResult, CrawlStats
from .relevance_analyzer import RelevanceAnalyzer
from core.validator import InputValidator
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class SmartCrawlResult(CrawlResult):
    """Extended crawl result with relevance information"""
    relevance_score: float = 0.0
    relevant_links: List[Tuple[str, float]] = field(default_factory=list)  # (url, score) pairs


class SmartWebCrawler(WebCrawler):
    """
    Enhanced web crawler that uses relevance analysis to intelligently
    select which links to follow.
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
        similarity_threshold: float = 0.3,
        min_relevance_score: float = 0.4,
        analyze_content_depth: bool = True
    ):
        """
        Initialize smart web crawler.
        
        Args:
            rate_limiter: Rate limiter instance
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            allowed_domains: List of allowed domains
            excluded_patterns: URL patterns to exclude
            follow_external_links: Whether to follow external links
            keywords: Keywords to search for
            similarity_threshold: Minimum similarity for relevance analyzer
            min_relevance_score: Minimum score to follow a link
            analyze_content_depth: Whether to fetch pages for deep content analysis
        """
        super().__init__(
            rate_limiter=rate_limiter,
            max_depth=max_depth,
            max_pages=max_pages,
            allowed_domains=allowed_domains,
            excluded_patterns=excluded_patterns,
            follow_external_links=follow_external_links,
            keywords=keywords
        )
        
        self.relevance_analyzer = RelevanceAnalyzer(similarity_threshold)
        self.min_relevance_score = min_relevance_score
        self.analyze_content_depth = analyze_content_depth
        self.seed_analyzed = False
        
        # Track relevance scores for analysis
        self.url_relevance_scores: Dict[str, float] = {}
        
    def crawl(
        self,
        start_url: str,
        fetch_callback: Callable[[str], requests.Response],
        parse_callback: Optional[Callable[[str, str], Any]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Crawl website starting from a URL, using relevance to guide exploration.
        
        Args:
            start_url: URL to start crawling from
            fetch_callback: Function to fetch page content
            parse_callback: Optional function to parse page content
            progress_callback: Optional function to report progress
            
        Returns:
            Dict containing results and statistics
        """
        # Initialize crawl
        self.visited_urls.clear()
        self.queued_urls.clear()
        self.results.clear()
        self.stats = CrawlStats()
        self.url_relevance_scores.clear()
        self.seed_analyzed = False
        
        # Validate and normalize start URL
        valid, normalized_url = self.validator.validate_url(start_url)
        if not valid:
            raise ValueError(f"Invalid start URL: {start_url}")
        
        # Set initial allowed domain if not specified
        if self.allowed_domains is None and not self.follow_external_links:
            parsed = urlparse(normalized_url)
            self.allowed_domains = [parsed.netloc]
        
        # Queue the start URL
        self.queued_urls.append((normalized_url, 0))  # (url, depth)
        
        logger.info(f"Starting smart crawl from: {normalized_url}")
        logger.info(f"Settings: max_depth={self.max_depth}, max_pages={self.max_pages}")
        logger.info(f"Relevance threshold: {self.min_relevance_score}")
        
        # Main crawl loop
        while self.queued_urls and self.stats.total_pages < self.max_pages:
            url, depth = self.queued_urls.popleft()
            
            # Skip if already visited or exceeds depth
            if url in self.visited_urls or depth > self.max_depth:
                continue
            
            # Mark as visited
            self.visited_urls.add(url)
            self.stats.total_pages += 1
            
            # Report progress
            if progress_callback:
                progress_callback(
                    self.stats.total_pages,
                    self.max_pages,
                    f"Crawling: {self._truncate_url(url)}"
                )
            
            # Apply rate limiting
            domain = urlparse(url).netloc
            wait_time = self.rate_limiter.wait_if_needed(domain)
            if wait_time > 0:
                logger.debug(f"Rate limited: waited {wait_time:.2f}s for {domain}")
            
            # Fetch and process page
            result = self._process_page(
                url, depth, fetch_callback, parse_callback
            )
            
            self.results.append(result)
            
            if result.is_successful():
                self.stats.successful_pages += 1
                
                # Analyze seed content on first successful page
                if not self.seed_analyzed and result.content:
                    logger.info("Analyzing seed content for relevance baseline")
                    self.relevance_analyzer.analyze_seed_content(url, result.content)
                    self.seed_analyzed = True
                
                # Extract and queue relevant links
                if result.links and self.seed_analyzed:
                    self._queue_relevant_links(
                        result.links, url, depth, result.content
                    )
                
                # Check for keyword matches
                if self.keywords and result.content:
                    self._check_keywords(result)
            else:
                self.stats.failed_pages += 1
        
        # Compile final results
        crawl_results = {
            'results': self.results,
            'stats': {
                'total_pages': self.stats.total_pages,
                'successful_pages': self.stats.successful_pages,
                'failed_pages': self.stats.failed_pages,
                'matched_pages': self.stats.matched_pages,
                'total_links_found': self.stats.total_links_found,
                'duration': self.stats.duration,
                'success_rate': self.stats.success_rate,
                'relevance_scores': self.url_relevance_scores
            },
            'visited_urls': list(self.visited_urls),
            'queued_urls': list(self.queued_urls)
        }
        
        logger.info(f"Smart crawl completed: {self.stats.successful_pages} pages crawled")
        logger.info(f"Average relevance score: {self._calculate_avg_relevance():.2f}")
        
        return crawl_results
    
    def _process_page(
        self,
        url: str,
        depth: int,
        fetch_callback: Callable,
        parse_callback: Optional[Callable]
    ) -> SmartCrawlResult:
        """Process a single page with relevance tracking."""
        result = SmartCrawlResult(url=url, depth=depth)
        
        try:
            # Fetch page
            response = fetch_callback(url)
            
            # Extract content
            soup = BeautifulSoup(response.text, 'html.parser')
            result.title = soup.title.string if soup.title else None
            result.content = response.text
            
            # Extract links with relevance analysis
            links_with_scores = self._extract_relevant_links(soup, url)
            result.links = [link for link, _ in links_with_scores]
            result.relevant_links = links_with_scores
            
            self.stats.total_links_found += len(result.links)
            
            # Parse content if callback provided
            if parse_callback:
                result.metadata['parsed_data'] = parse_callback(url, response.text)
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            result.error = str(e)
        
        return result
    
    def _check_keywords(self, result: SmartCrawlResult) -> None:
        """Check for keyword matches in the result content."""
        if not self.keywords or not result.content:
            return
        
        content_lower = result.content.lower()
        result.matched_keywords = []
        
        for keyword in self.keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
        
        if result.matched_keywords:
            self.stats.matched_pages += 1
    
    def _extract_relevant_links(
        self,
        soup: BeautifulSoup,
        base_url: str
    ) -> List[Tuple[str, float]]:
        """Extract links with relevance scores."""
        links_with_scores = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip anchors and javascript
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            
            # Normalize URL
            absolute_url = self._normalize_url(absolute_url)
            
            # Check if URL should be considered
            if not self._should_follow_url(absolute_url):
                continue
            
            # Calculate relevance score
            link_text = link.get_text(strip=True)
            link_context = self.relevance_analyzer.get_link_context(link)
            
            relevance_score = self.relevance_analyzer.calculate_relevance_score(
                absolute_url,
                link_text=link_text,
                link_context=link_context
            )
            
            # Store score for analysis
            self.url_relevance_scores[absolute_url] = relevance_score
            
            # Only include if relevant enough
            if relevance_score >= self.min_relevance_score:
                links_with_scores.append((absolute_url, relevance_score))
                logger.debug(
                    f"Relevant link found: {self._truncate_url(absolute_url)} "
                    f"(score: {relevance_score:.2f}, text: '{link_text[:30]}')"
                )
        
        # Sort by relevance score (highest first)
        links_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        return links_with_scores
    
    def _queue_relevant_links(
        self,
        links: List[str],
        current_url: str,
        current_depth: int,
        page_content: str
    ) -> None:
        """Queue only the most relevant links for crawling."""
        # Get links with scores from current page
        soup = BeautifulSoup(page_content, 'html.parser')
        links_with_scores = self._extract_relevant_links(soup, current_url)
        
        # Queue links based on relevance
        queued_count = 0
        for link, score in links_with_scores:
            if link not in self.visited_urls and score >= self.min_relevance_score:
                # Prioritize high-relevance links by adding them to front of queue
                if score >= 0.7:
                    self.queued_urls.appendleft((link, current_depth + 1))
                else:
                    self.queued_urls.append((link, current_depth + 1))
                
                queued_count += 1
                
                # Limit number of links queued per page
                if queued_count >= 10:  # Configurable limit
                    break
        
        logger.debug(f"Queued {queued_count} relevant links from {self._truncate_url(current_url)}")
    
    def _should_follow_url(self, url: str) -> bool:
        """Check if URL should be followed based on rules and relevance."""
        # First apply parent class rules
        if not super()._should_follow_url(url):
            return False
        
        # Additional smart filtering
        parsed = urlparse(url)
        
        # Skip if URL is too deep (path depth)
        path_depth = len([p for p in parsed.path.split('/') if p])
        if path_depth > 6:  # Configurable
            return False
        
        # Skip if URL has too many parameters
        if parsed.query and len(parsed.query.split('&')) > 3:
            return False
        
        return True
    
    def _calculate_avg_relevance(self) -> float:
        """Calculate average relevance score of crawled URLs."""
        if not self.url_relevance_scores:
            return 0.0
        
        scores = list(self.url_relevance_scores.values())
        return sum(scores) / len(scores)
    
    def _truncate_url(self, url: str, max_length: int = 60) -> str:
        """Truncate URL for display."""
        if len(url) <= max_length:
            return url
        return url[:max_length - 3] + "..."
    
    def get_relevance_report(self) -> Dict[str, Any]:
        """Generate a report on relevance analysis."""
        if not self.url_relevance_scores:
            return {}
        
        scores = list(self.url_relevance_scores.values())
        sorted_urls = sorted(
            self.url_relevance_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'average_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'total_analyzed': len(scores),
            'above_threshold': sum(1 for s in scores if s >= self.min_relevance_score),
            'top_relevant_urls': sorted_urls[:10],
            'least_relevant_urls': sorted_urls[-10:]
        }