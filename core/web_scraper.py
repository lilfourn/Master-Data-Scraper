"""
Web scraper implementation using the base scraper

This module provides a concrete implementation of the BaseScraper
for general web scraping tasks.
"""

from typing import Any, Dict, List, Union, Optional
import logging
from pathlib import Path

from .scraper import BaseScraper
from .parser import HTMLParser
from .validator import InputValidator
from .exporter import ExporterFactory
from .organizer import FileOrganizer
from .fast_crawler import FastCrawler
from utils.rate_limiter import RateLimiter
from config import get_settings

logger = logging.getLogger(__name__)


class WebScraper(BaseScraper):
    """
    Concrete implementation of BaseScraper for web scraping
    
    This class combines all the core components to provide
    a complete web scraping solution.
    """
    
    def __init__(self, 
                 rate_limiter: Optional[RateLimiter] = None,
                 file_organizer: Optional[FileOrganizer] = None,
                 **kwargs):
        """
        Initialize the web scraper
        
        Args:
            rate_limiter: Optional rate limiter instance
            file_organizer: Optional file organizer instance
            **kwargs: Additional arguments for BaseScraper
        """
        # Load settings
        self.settings = get_settings()
        
        # Set defaults from settings
        kwargs.setdefault('timeout', self.settings.timeout)
        kwargs.setdefault('max_retries', self.settings.max_retries)
        kwargs.setdefault('user_agent', self.settings.user_agent)
        kwargs.setdefault('verify_ssl', self.settings.verify_ssl)
        kwargs.setdefault('cache_ttl', self.settings.cache_ttl)
        
        super().__init__(**kwargs)
        
        # Initialize components with domain-specific settings
        domain_delays = self._load_domain_delays()
        self.rate_limiter = rate_limiter or RateLimiter(
            default_delay=self.settings.rate_limit_default,
            domain_delays=domain_delays
        )
        self.file_organizer = file_organizer or FileOrganizer(
            base_dir=Path(self.settings.data_dir)
        )
        
        # Validator instance
        self.validator = InputValidator()
    
    def _load_domain_delays(self) -> Dict[str, float]:
        """Load domain-specific rate limits from config"""
        try:
            import yaml
            config_path = Path("config/domains.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('rate_limits', {})
            return {}
        except Exception as e:
            logger.warning(f"Failed to load domain config: {e}")
            return {}
    
    def scrape(self, url: str, element_type: str, 
               save: bool = True, 
               export_format: str = "csv",
               preview: bool = False) -> Any:
        """
        Scrape specific elements from a URL
        
        Args:
            url: The URL to scrape
            element_type: The type of HTML element to extract
            save: Whether to save the scraped data
            export_format: Format to export data (csv, json, md, txt)
            preview: Whether to show a preview before saving
            
        Returns:
            Scraped data in appropriate format
            
        Raises:
            ValueError: If inputs are invalid
            requests.RequestException: If scraping fails
        """
        # Validate inputs
        valid_url, url = self.validator.validate_url(url, check_accessibility=False)
        if not valid_url:
            raise ValueError(f"Invalid URL: {url}")
        
        valid_element, element_type = self.validator.validate_element_type(element_type)
        if not valid_element:
            raise ValueError(f"Invalid element type: {element_type}")
        
        valid_format, export_format = self.validator.validate_format_type(export_format)
        if not valid_format:
            raise ValueError(f"Invalid export format: {export_format}")
        
        # Extract domain for rate limiting
        domain = self.validator.extract_domain(url)
        
        # Apply rate limiting
        wait_time = self.rate_limiter.wait_if_needed(domain)
        if wait_time > 0:
            logger.info(f"Rate limited: waited {wait_time:.2f}s for {domain}")
        
        try:
            # Fetch the page
            response = self.fetch(url)
            
            # Parse HTML with settings
            parser = HTMLParser(response.text, settings=self.settings)
            data = parser.parse(element_type)
            
            # Extract metadata if settings allow
            metadata = None
            page_title = None
            if self.settings.scrape_metadata:
                metadata = parser.extract_metadata()
                page_title = metadata.get('title')
            
            # Show preview if requested
            if preview:
                preview_text = parser.preview_element(element_type)
                logger.info(f"Preview:\n{preview_text}")
            
            # Save data if requested
            if save and data:
                filepath = self._save_data(url, element_type, export_format, data, 
                                         metadata=metadata, page_title=page_title)
                logger.info(f"Data saved to: {filepath}")
                
                # Update metadata
                extra_metadata = {
                    'element_count': self._count_elements(data)
                }
                if metadata and self.settings.include_page_info:
                    extra_metadata['page_metadata'] = metadata
                    
                self.file_organizer.update_metadata(
                    url=url,
                    filepath=filepath,
                    element_type=element_type,
                    format_type=export_format,
                    **extra_metadata
                )
            
            return data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise
    
    def scrape_multiple(self, urls: List[str], element_type: str, 
                       export_format: str = "csv") -> Dict[str, Any]:
        """
        Scrape multiple URLs
        
        Args:
            urls: List of URLs to scrape
            element_type: The type of HTML element to extract
            export_format: Format to export data
            
        Returns:
            Dictionary mapping URLs to their scraped data
        """
        results = {}
        
        for url in urls:
            try:
                data = self.scrape(url, element_type, save=True, 
                                 export_format=export_format)
                results[url] = {
                    'success': True,
                    'data': data,
                    'element_count': self._count_elements(data)
                }
            except Exception as e:
                results[url] = {
                    'success': False,
                    'error': str(e)
                }
                logger.error(f"Failed to scrape {url}: {e}")
        
        return results
    
    def crawl_and_scrape(self, start_url: str, element_type: str,
                        keywords: Optional[List[str]] = None,
                        export_format: str = "csv",
                        max_depth: int = 3,
                        max_pages: int = 50,
                        follow_external_links: bool = False,
                        progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Crawl a website and scrape data from matched pages
        
        Args:
            start_url: URL to start crawling from
            element_type: Type of element to scrape
            keywords: Keywords to search for in pages
            export_format: Format to export data
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            follow_external_links: Whether to follow external links
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with crawl results and scraped data
        """
        # Validate inputs
        valid_url, start_url = self.validator.validate_url(start_url, check_accessibility=False)
        if not valid_url:
            raise ValueError(f"Invalid URL: {start_url}")
        
        valid_element, element_type = self.validator.validate_element_type(element_type)
        if not valid_element:
            raise ValueError(f"Invalid element type: {element_type}")
        
        # Perform crawl and scrape
        result = super().crawl_and_scrape(
            start_url=start_url,
            element_type=element_type,
            keywords=keywords,
            max_depth=max_depth,
            max_pages=max_pages,
            follow_external_links=follow_external_links,
            progress_callback=progress_callback
        )
        
        # Save scraped data
        saved_files = []
        for page_data in result['data']:
            if page_data['data']:
                try:
                    # Generate filename for crawled page
                    filepath = self.file_organizer.generate_filename(
                        url=page_data['url'],
                        element_type=element_type,
                        format_type=export_format,
                        prefix=f"crawl_{page_data['depth']}_"
                    )
                    
                    # Export data
                    exporter = ExporterFactory.create_exporter(export_format)
                    saved_path = exporter.export(page_data['data'], filepath)
                    saved_files.append(saved_path)
                    
                    # Update metadata
                    self.file_organizer.update_metadata(
                        url=page_data['url'],
                        filepath=saved_path,
                        element_type=element_type,
                        format_type=export_format,
                        element_count=self._count_elements(page_data['data']),
                        extra_info={
                            'crawl_depth': page_data['depth'],
                            'matched_keywords': page_data['keywords']
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to save data from {page_data['url']}: {e}")
        
        # Add saved files info to result
        result['saved_files'] = saved_files
        
        return result
    
    def fast_crawl_and_scrape(self, start_url: str, element_type: str,
                             keywords: Optional[List[str]] = None,
                             export_format: str = "csv",
                             max_depth: int = 3,
                             max_pages: int = 50,
                             max_workers: int = 10,
                             progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Fast crawl and scrape using concurrent requests
        
        Args:
            start_url: URL to start crawling from
            element_type: Type of element to scrape
            keywords: Keywords to search for
            export_format: Format to export data
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            max_workers: Number of concurrent workers
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with crawl results and scraped data
        """
        # Validate inputs
        valid_url, start_url = self.validator.validate_url(start_url, check_accessibility=False)
        if not valid_url:
            raise ValueError(f"Invalid URL: {start_url}")
        
        valid_element, element_type = self.validator.validate_element_type(element_type)
        if not valid_element:
            raise ValueError(f"Invalid element type: {element_type}")
        
        # Create fast crawler with domain-aware rate limiting
        domain_delays = self._load_domain_delays()
        crawler = FastCrawler(
            max_workers=max_workers,
            rate_limiter=RateLimiter(
                default_delay=0.1,  # 100ms default
                domain_delays=domain_delays  # Domain-specific delays
            ),
            max_depth=max_depth,
            max_pages=max_pages,
            keywords=keywords,
            min_delay=0.1
        )
        
        # Start crawling
        crawl_results = crawler.crawl_concurrent(
            start_url=start_url,
            fetch_func=self.fetch,
            progress_callback=progress_callback
        )
        
        # Process results and scrape data
        scraped_data = []
        saved_files = []
        
        for result in crawl_results:
            if result.is_successful() and (not keywords or result.matched_keywords):
                try:
                    # Get HTML from cache or fetch if needed
                    html = crawler.html_cache.get(result.url)
                    if not html:
                        # Fallback: fetch the page again
                        response = self.fetch(result.url)
                        html = response.text if response else None
                    
                    if html:
                        # Parse HTML and extract elements
                        parser = HTMLParser(html)
                        data = parser.parse(element_type)
                    else:
                        continue
                    
                    if data:
                        page_info = {
                            'url': result.url,
                            'title': result.title,
                            'depth': result.depth,
                            'keywords': result.matched_keywords,
                            'data': data
                        }
                        scraped_data.append(page_info)
                        
                        # Save data
                        filepath = self.file_organizer.generate_filename(
                            url=result.url,
                            element_type=element_type,
                            format_type=export_format,
                            prefix=f"fast_crawl_{result.depth}_"
                        )
                        
                        exporter = ExporterFactory.create_exporter(export_format)
                        saved_path = exporter.export(data, filepath)
                        saved_files.append(saved_path)
                        
                        # Update metadata
                        self.file_organizer.update_metadata(
                            url=result.url,
                            filepath=saved_path,
                            element_type=element_type,
                            format_type=export_format,
                            element_count=self._count_elements(data),
                            extra_info={
                                'crawl_depth': result.depth,
                                'matched_keywords': result.matched_keywords,
                                'fast_crawl': True
                            }
                        )
                except Exception as e:
                    logger.error(f"Failed to process {result.url}: {e}")
        
        stats = crawler.stats
        
        return {
            'crawl_stats': {
                'total_pages': stats.total_pages,
                'successful_pages': stats.successful_pages,
                'failed_pages': stats.failed_pages,
                'matched_pages': stats.matched_pages,
                'duration': stats.duration
            },
            'scraped_pages': len(scraped_data),
            'data': scraped_data,
            'saved_files': saved_files
        }
    
    def _save_data(self, url: str, element_type: str, 
                   format_type: str, data: Any,
                   metadata: Optional[Dict[str, Any]] = None,
                   page_title: Optional[str] = None) -> Path:
        """
        Save scraped data to file
        
        Args:
            url: Source URL
            element_type: Type of element scraped
            format_type: Export format
            data: Data to save
            metadata: Optional page metadata
            page_title: Optional page title
            
        Returns:
            Path to saved file
        """
        # Generate filename using settings
        filepath = self.file_organizer.generate_filename(
            url=url,
            element_type=element_type,
            format_type=format_type,
            settings=self.settings,
            page_title=page_title
        )
        
        # Create exporter
        exporter = ExporterFactory.create_exporter(format_type)
        
        # Export data
        saved_path = exporter.export(data, filepath)
        
        return saved_path
    
    def _count_elements(self, data: Any) -> int:
        """Count number of elements in scraped data"""
        if isinstance(data, list):
            return len(data)
        elif hasattr(data, 'shape'):  # DataFrame
            return data.shape[0]
        elif isinstance(data, dict):
            return len(data)
        else:
            return 1
    
    def get_domain_history(self, domain: str) -> Dict[str, Any]:
        """
        Get scraping history for a domain
        
        Args:
            domain: Domain name
            
        Returns:
            Domain statistics and history
        """
        return self.file_organizer.get_domain_stats(domain)
    
    def smart_crawl_and_scrape(self, start_url: str, element_type: str,
                              keywords: Optional[List[str]] = None,
                              export_format: str = "csv",
                              max_depth: int = 3,
                              max_pages: int = 50,
                              similarity_threshold: float = 0.3,
                              min_relevance_score: float = 0.4,
                              follow_external_links: bool = False,
                              progress_callback: Optional[Any] = None) -> Dict[str, Any]:
        """
        Smart crawl using relevance analysis to stay focused on related content
        
        Args:
            start_url: URL to start crawling from
            element_type: Type of element to scrape
            keywords: Optional keywords to enhance relevance
            export_format: Format to export data
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            similarity_threshold: Minimum similarity for relevance analyzer
            min_relevance_score: Minimum score to follow a link
            follow_external_links: Whether to follow external links
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with crawl results and scraped data
        """
        # Import here to avoid circular imports
        from .smart_crawler import SmartWebCrawler
        
        # Validate inputs
        valid_url, start_url = self.validator.validate_url(start_url, check_accessibility=False)
        if not valid_url:
            raise ValueError(f"Invalid URL: {start_url}")
        
        valid_element, element_type = self.validator.validate_element_type(element_type)
        if not valid_element:
            raise ValueError(f"Invalid element type: {element_type}")
        
        # Create smart crawler
        crawler = SmartWebCrawler(
            rate_limiter=self.rate_limiter,
            max_depth=max_depth,
            max_pages=max_pages,
            keywords=keywords,
            similarity_threshold=similarity_threshold,
            min_relevance_score=min_relevance_score,
            follow_external_links=follow_external_links
        )
        
        logger.info(f"Starting smart crawl from {start_url}")
        logger.info(f"Relevance threshold: {min_relevance_score}")
        
        # Start crawling
        crawl_results = crawler.crawl(
            start_url=start_url,
            fetch_callback=self.fetch,
            progress_callback=progress_callback
        )
        
        # Process results and scrape data
        scraped_data = []
        saved_files = []
        
        for result in crawl_results['results']:
            if result.is_successful():
                try:
                    # Parse HTML and extract elements
                    parser = HTMLParser(result.content)
                    data = parser.parse(element_type)
                    
                    if data:
                        page_info = {
                            'url': result.url,
                            'title': result.title,
                            'depth': result.depth,
                            'relevance_score': getattr(result, 'relevance_score', 0.0),
                            'matched_keywords': result.matched_keywords,
                            'data': data
                        }
                        scraped_data.append(page_info)
                        
                        # Save data with relevance info in filename
                        relevance_str = f"rel{int(result.relevance_score * 100):03d}"
                        filepath = self.file_organizer.generate_filename(
                            url=result.url,
                            element_type=element_type,
                            format_type=export_format,
                            prefix=f"smart_{relevance_str}_"
                        )
                        
                        exporter = ExporterFactory.create_exporter(export_format)
                        saved_path = exporter.export(data, filepath)
                        saved_files.append(saved_path)
                        
                        # Update metadata with relevance info
                        self.file_organizer.update_metadata(
                            url=result.url,
                            filepath=saved_path,
                            element_type=element_type,
                            format_type=export_format,
                            element_count=self._count_elements(data),
                            extra_info={
                                'crawl_depth': result.depth,
                                'relevance_score': result.relevance_score,
                                'matched_keywords': result.matched_keywords,
                                'smart_crawl': True
                            }
                        )
                except Exception as e:
                    logger.error(f"Failed to process {result.url}: {e}")
        
        # Get relevance report
        relevance_report = crawler.get_relevance_report()
        
        return {
            'crawl_stats': crawl_results['stats'],
            'relevance_report': relevance_report,
            'scraped_pages': len(scraped_data),
            'data': scraped_data,
            'saved_files': saved_files
        }