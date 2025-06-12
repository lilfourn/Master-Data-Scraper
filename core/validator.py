"""
Input validation module for Master Data Scraper

This module provides validation for URLs, element types, file paths,
and other user inputs.
"""

import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import validators
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates user inputs for the scraper"""
    
    # Supported HTML elements
    SUPPORTED_ELEMENTS = [
        'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'li', 'ul', 'ol', 'a', 'img', 'div', 'span'
    ]
    
    # Supported export formats
    SUPPORTED_FORMATS = ['csv', 'json', 'md', 'markdown', 'txt', 'text']
    
    @staticmethod
    def validate_url(url: str, check_accessibility: bool = True) -> Tuple[bool, str]:
        """
        Validate URL format and optionally check accessibility
        
        Args:
            url: URL to validate
            check_accessibility: Whether to check if URL is accessible
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if URL is provided
        if not url:
            return False, "URL cannot be empty"
        
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate URL format
        if not validators.url(url):
            return False, "Invalid URL format"
        
        # Check accessibility if requested
        if check_accessibility:
            try:
                # Use a browser-like user agent to avoid blocks
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = requests.head(url, timeout=10, allow_redirects=True, headers=headers)
                
                if response.status_code == 429:
                    # Extract domain for specific advice
                    domain = urlparse(url).netloc
                    return False, (f"Rate limit error (429) from {domain}. "
                                 f"This site has rate limiting protection. "
                                 f"Try again in a few seconds or adjust the rate limit in config/domains.yaml")
                elif response.status_code == 403:
                    return False, (f"Access forbidden (403) from {urlparse(url).netloc}. "
                                 f"This site may block automated requests. "
                                 f"Consider using different headers or checking robots.txt")
                elif response.status_code >= 400:
                    return False, f"URL returned status code {response.status_code}"
            except requests.exceptions.Timeout:
                return False, "URL request timed out after 10 seconds"
            except requests.exceptions.ConnectionError:
                return False, "Could not connect to the URL (connection error)"
            except requests.RequestException as e:
                return False, f"URL is not accessible: {str(e)}"
        
        return True, url
    
    @staticmethod
    def validate_element_type(element_type: str) -> Tuple[bool, str]:
        """
        Validate HTML element type
        
        Args:
            element_type: Element type to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not element_type:
            return False, "Element type cannot be empty"
        
        element_type = element_type.lower().strip()
        
        # Check if it's a supported element
        if element_type in InputValidator.SUPPORTED_ELEMENTS:
            return True, element_type
        
        # Check if it's a valid CSS selector
        if InputValidator._is_valid_css_selector(element_type):
            return True, element_type
        
        return False, (f"Invalid element type. Supported types: "
                      f"{', '.join(InputValidator.SUPPORTED_ELEMENTS)} "
                      f"or a valid CSS selector")
    
    @staticmethod
    def validate_format_type(format_type: str) -> Tuple[bool, str]:
        """
        Validate export format type
        
        Args:
            format_type: Format type to validate
            
        Returns:
            Tuple of (is_valid, normalized_format)
        """
        if not format_type:
            return False, "Format type cannot be empty"
        
        format_type = format_type.lower().strip()
        
        # Normalize format aliases
        format_map = {
            'markdown': 'md',
            'text': 'txt'
        }
        
        normalized = format_map.get(format_type, format_type)
        
        if normalized not in ['csv', 'json', 'md', 'txt']:
            return False, (f"Invalid format type. Supported formats: "
                          f"{', '.join(InputValidator.SUPPORTED_FORMATS)}")
        
        return True, normalized
    
    @staticmethod
    def validate_file_path(path: str, must_exist: bool = False) -> Tuple[bool, str]:
        """
        Validate file path
        
        Args:
            path: File path to validate
            must_exist: Whether the path must already exist
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path_obj = Path(path)
            
            # Check if path is absolute and within safe boundaries
            if path_obj.is_absolute():
                return False, "Absolute paths are not allowed for security reasons"
            
            # Check for path traversal attempts
            if '..' in path_obj.parts:
                return False, "Path traversal is not allowed"
            
            # Check if path exists if required
            if must_exist and not path_obj.exists():
                return False, f"Path does not exist: {path}"
            
            # Check if parent directory exists for new files
            if not must_exist and not path_obj.parent.exists():
                return False, f"Parent directory does not exist: {path_obj.parent}"
            
            return True, str(path_obj)
            
        except Exception as e:
            return False, f"Invalid path: {str(e)}"
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract domain from URL
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain name or None if invalid
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove port if present
            domain = domain.split(':')[0]
            
            return domain if domain else None
            
        except Exception:
            return None
    
    @staticmethod
    def _is_valid_css_selector(selector: str) -> bool:
        """
        Check if a string is a valid CSS selector
        
        Args:
            selector: CSS selector string
            
        Returns:
            True if valid CSS selector
        """
        # Basic CSS selector validation
        # This is a simplified check - full CSS selector validation is complex
        css_pattern = re.compile(
            r'^[a-zA-Z0-9\s\-_#.\[\]="\',:()>+~*]+$'
        )
        
        return bool(css_pattern.match(selector))
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 255) -> str:
        """
        Sanitize user input for safety
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
        
        # Limit length
        text = text[:max_length]
        
        # Strip whitespace
        text = text.strip()
        
        return text