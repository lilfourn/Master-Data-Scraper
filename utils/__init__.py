"""
Utility modules for Master Data Scraper

This package contains utility functions for CLI interface, logging,
rate limiting, caching, robots.txt compliance, user-agent rotation,
and custom exceptions.
"""

from .rate_limiter import RateLimiter, AdaptiveRateLimiter, RequestQueue
from .cache import ResponseCache
from .logger import setup_logging, get_logger, log_exception
from .cli import InteractiveCLI, Theme
from .robots import RobotsChecker, RobotsCompliantScraper
from .user_agents import UserAgentRotator, UserAgentMiddleware
from .exceptions import (
    ScraperException, NetworkError, ValidationError, ParsingError,
    ExportError, RateLimitError, RobotsError, ConfigurationError,
    CacheError, TimeoutError, AuthenticationError,
    ErrorRecovery, handle_scraper_exception
)

__all__ = [
    # Rate limiting
    'RateLimiter', 'AdaptiveRateLimiter', 'RequestQueue',
    
    # Caching
    'ResponseCache',
    
    # Logging
    'setup_logging', 'get_logger', 'log_exception',
    
    # CLI
    'InteractiveCLI', 'Theme',
    
    # Robots.txt
    'RobotsChecker', 'RobotsCompliantScraper',
    
    # User agents
    'UserAgentRotator', 'UserAgentMiddleware',
    
    # Exceptions
    'ScraperException', 'NetworkError', 'ValidationError', 'ParsingError',
    'ExportError', 'RateLimitError', 'RobotsError', 'ConfigurationError',
    'CacheError', 'TimeoutError', 'AuthenticationError',
    'ErrorRecovery', 'handle_scraper_exception'
]