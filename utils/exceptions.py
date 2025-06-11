"""
Custom exception classes for Master Data Scraper

This module defines custom exceptions for better error handling
and user-friendly error messages.
"""

from typing import Optional, Dict, Any


class ScraperException(Exception):
    """Base exception for all scraper-related errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize scraper exception
        
        Args:
            message: Error message
            details: Optional dictionary with error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation of the exception"""
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class NetworkError(ScraperException):
    """Network-related errors"""
    
    def __init__(self, message: str, url: Optional[str] = None, 
                 status_code: Optional[int] = None, **kwargs):
        """
        Initialize network error
        
        Args:
            message: Error message
            url: URL that caused the error
            status_code: HTTP status code if available
            **kwargs: Additional details
        """
        details = kwargs
        if url:
            details['url'] = url
        if status_code:
            details['status_code'] = status_code
        
        super().__init__(message, details)


class ValidationError(ScraperException):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, 
                 value: Optional[Any] = None, **kwargs):
        """
        Initialize validation error
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            **kwargs: Additional details
        """
        details = kwargs
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        
        super().__init__(message, details)


class ParsingError(ScraperException):
    """HTML parsing errors"""
    
    def __init__(self, message: str, element_type: Optional[str] = None,
                 selector: Optional[str] = None, **kwargs):
        """
        Initialize parsing error
        
        Args:
            message: Error message
            element_type: Type of element being parsed
            selector: CSS selector or element identifier
            **kwargs: Additional details
        """
        details = kwargs
        if element_type:
            details['element_type'] = element_type
        if selector:
            details['selector'] = selector
        
        super().__init__(message, details)


class ExportError(ScraperException):
    """Data export errors"""
    
    def __init__(self, message: str, format_type: Optional[str] = None,
                 file_path: Optional[str] = None, **kwargs):
        """
        Initialize export error
        
        Args:
            message: Error message
            format_type: Export format that failed
            file_path: Target file path
            **kwargs: Additional details
        """
        details = kwargs
        if format_type:
            details['format_type'] = format_type
        if file_path:
            details['file_path'] = file_path
        
        super().__init__(message, details)


class RateLimitError(NetworkError):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 retry_after: Optional[float] = None, **kwargs):
        """
        Initialize rate limit error
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            **kwargs: Additional details
        """
        if retry_after:
            kwargs['retry_after'] = retry_after
            message = f"{message}. Retry after {retry_after}s"
        
        super().__init__(message, status_code=429, **kwargs)


class RobotsError(ScraperException):
    """Robots.txt compliance errors"""
    
    def __init__(self, message: str = "Access denied by robots.txt", 
                 url: Optional[str] = None, **kwargs):
        """
        Initialize robots error
        
        Args:
            message: Error message
            url: URL that is disallowed
            **kwargs: Additional details
        """
        details = kwargs
        if url:
            details['url'] = url
            message = f"{message}: {url}"
        
        super().__init__(message, details)


class ConfigurationError(ScraperException):
    """Configuration-related errors"""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 config_file: Optional[str] = None, **kwargs):
        """
        Initialize configuration error
        
        Args:
            message: Error message
            config_key: Configuration key that caused error
            config_file: Configuration file path
            **kwargs: Additional details
        """
        details = kwargs
        if config_key:
            details['config_key'] = config_key
        if config_file:
            details['config_file'] = config_file
        
        super().__init__(message, details)


class CacheError(ScraperException):
    """Cache-related errors"""
    
    def __init__(self, message: str, cache_key: Optional[str] = None, **kwargs):
        """
        Initialize cache error
        
        Args:
            message: Error message
            cache_key: Cache key that caused error
            **kwargs: Additional details
        """
        details = kwargs
        if cache_key:
            details['cache_key'] = cache_key
        
        super().__init__(message, details)


class TimeoutError(NetworkError):
    """Request timeout errors"""
    
    def __init__(self, message: str = "Request timed out", 
                 timeout: Optional[float] = None, **kwargs):
        """
        Initialize timeout error
        
        Args:
            message: Error message
            timeout: Timeout value in seconds
            **kwargs: Additional details
        """
        if timeout:
            kwargs['timeout'] = timeout
            message = f"{message} after {timeout}s"
        
        super().__init__(message, **kwargs)


class AuthenticationError(NetworkError):
    """Authentication-related errors"""
    
    def __init__(self, message: str = "Authentication failed", 
                 auth_type: Optional[str] = None, **kwargs):
        """
        Initialize authentication error
        
        Args:
            message: Error message
            auth_type: Type of authentication that failed
            **kwargs: Additional details
        """
        if auth_type:
            kwargs['auth_type'] = auth_type
        
        super().__init__(message, status_code=401, **kwargs)


# Error recovery strategies
class ErrorRecovery:
    """Strategies for recovering from errors"""
    
    @staticmethod
    def get_user_friendly_message(exception: Exception) -> str:
        """
        Get a user-friendly error message
        
        Args:
            exception: Exception instance
            
        Returns:
            User-friendly error message
        """
        error_messages = {
            NetworkError: "Network connection failed. Please check your internet connection.",
            ValidationError: "Invalid input provided. Please check your input and try again.",
            ParsingError: "Failed to extract data from the webpage. The page structure might have changed.",
            ExportError: "Failed to save data. Please check file permissions and disk space.",
            RateLimitError: "Too many requests. Please wait before trying again.",
            RobotsError: "Access denied. This website does not allow scraping of this page.",
            ConfigurationError: "Configuration error. Please check your settings.",
            CacheError: "Cache operation failed. Try clearing the cache.",
            TimeoutError: "Request took too long. The website might be slow or unresponsive.",
            AuthenticationError: "Authentication failed. Please check your credentials.",
        }
        
        for error_type, message in error_messages.items():
            if isinstance(exception, error_type):
                return message
        
        # Generic message for unknown errors
        return "An unexpected error occurred. Please try again or contact support."
    
    @staticmethod
    def suggest_recovery_action(exception: Exception) -> str:
        """
        Suggest a recovery action for the error
        
        Args:
            exception: Exception instance
            
        Returns:
            Suggested recovery action
        """
        recovery_actions = {
            NetworkError: "Try: 1) Check internet connection, 2) Verify the URL, 3) Try again later",
            ValidationError: "Try: 1) Check the URL format, 2) Verify element type, 3) Check file paths",
            ParsingError: "Try: 1) Verify the webpage loads correctly, 2) Try a different element type, 3) Check if the website structure changed",
            ExportError: "Try: 1) Check disk space, 2) Verify write permissions, 3) Try a different export format",
            RateLimitError: "Try: 1) Wait before retrying, 2) Reduce request frequency, 3) Check rate limit settings",
            RobotsError: "Try: 1) Check robots.txt for allowed pages, 2) Use a different URL, 3) Contact website owner for permission",
            ConfigurationError: "Try: 1) Reset to default settings, 2) Check configuration file syntax, 3) Verify environment variables",
            CacheError: "Try: 1) Clear the cache with --clear-cache, 2) Check disk space, 3) Verify cache directory permissions",
            TimeoutError: "Try: 1) Increase timeout setting, 2) Check website status, 3) Try during off-peak hours",
            AuthenticationError: "Try: 1) Verify credentials, 2) Check authentication method, 3) Refresh authentication tokens",
        }
        
        for error_type, action in recovery_actions.items():
            if isinstance(exception, error_type):
                return action
        
        return "Try: 1) Check the error details, 2) Restart the application, 3) Check the documentation"


# Exception handlers for the application
def handle_scraper_exception(exception: Exception, console=None) -> None:
    """
    Handle scraper exceptions with user-friendly output
    
    Args:
        exception: Exception to handle
        console: Rich console instance for output
    """
    from rich.console import Console
    from rich.panel import Panel
    
    if console is None:
        console = Console()
    
    # Get user-friendly message and recovery suggestion
    friendly_message = ErrorRecovery.get_user_friendly_message(exception)
    recovery_action = ErrorRecovery.suggest_recovery_action(exception)
    
    # Create error panel
    error_content = f"[bold red]Error:[/bold red] {friendly_message}\n\n"
    
    if isinstance(exception, ScraperException) and exception.details:
        error_content += "[yellow]Details:[/yellow]\n"
        for key, value in exception.details.items():
            error_content += f"  • {key}: {value}\n"
        error_content += "\n"
    
    error_content += f"[green]Suggested Action:[/green]\n{recovery_action}"
    
    panel = Panel(
        error_content,
        title="⚠️  Error Occurred",
        border_style="red",
        expand=False
    )
    
    console.print(panel)
    
    # Log the full exception for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Exception: {type(exception).__name__}: {str(exception)}", exc_info=True)