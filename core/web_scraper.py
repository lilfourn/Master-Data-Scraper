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
        settings = get_settings()
        
        # Set defaults from settings
        kwargs.setdefault('timeout', settings.timeout)
        kwargs.setdefault('max_retries', settings.max_retries)
        kwargs.setdefault('user_agent', settings.user_agent)
        kwargs.setdefault('verify_ssl', settings.verify_ssl)
        kwargs.setdefault('cache_ttl', settings.cache_ttl)
        
        super().__init__(**kwargs)
        
        # Initialize components
        self.rate_limiter = rate_limiter or RateLimiter(
            default_delay=settings.rate_limit_default
        )
        self.file_organizer = file_organizer or FileOrganizer(
            base_dir=Path(settings.data_dir)
        )
        
        # Validator instance
        self.validator = InputValidator()
    
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
            
            # Parse HTML
            parser = HTMLParser(response.text)
            data = parser.parse(element_type)
            
            # Show preview if requested
            if preview:
                preview_text = parser.preview_element(element_type)
                logger.info(f"Preview:\n{preview_text}")
            
            # Save data if requested
            if save and data:
                filepath = self._save_data(url, element_type, export_format, data)
                logger.info(f"Data saved to: {filepath}")
                
                # Update metadata
                self.file_organizer.update_metadata(
                    url=url,
                    filepath=filepath,
                    element_type=element_type,
                    format_type=export_format,
                    element_count=self._count_elements(data)
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
    
    def _save_data(self, url: str, element_type: str, 
                   format_type: str, data: Any) -> Path:
        """
        Save scraped data to file
        
        Args:
            url: Source URL
            element_type: Type of element scraped
            format_type: Export format
            data: Data to save
            
        Returns:
            Path to saved file
        """
        # Generate filename
        filepath = self.file_organizer.generate_filename(
            url=url,
            element_type=element_type,
            format_type=format_type
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