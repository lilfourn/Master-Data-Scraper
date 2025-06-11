"""
Logging configuration module for Master Data Scraper

This module sets up logging with Rich handlers for beautiful
console output and file logging with rotation.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
from typing import Optional, Dict, Any

console = Console()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Path = Path("Data/_logs"),
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Custom log file name (defaults to scraper_YYYY-MM-DD.log)
        log_dir: Directory for log files
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("master_data_scraper")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler with Rich
    if enable_console:
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        console_handler.setLevel(getattr(logging, log_level.upper()))
        logger.addHandler(console_handler)
    
    # File handler
    if enable_file:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        if log_file is None:
            log_file = f"scraper_{datetime.now().strftime('%Y-%m-%d')}.log"
        
        log_path = log_dir / log_file
        
        # Use rotating file handler
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Also configure root logger to prevent duplicate logs
    logging.getLogger().handlers.clear()
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"master_data_scraper.{name}")


class LogContext:
    """Context manager for temporary log level changes"""
    
    def __init__(self, logger: logging.Logger, level: str):
        self.logger = logger
        self.new_level = getattr(logging, level.upper())
        self.old_level = logger.level
    
    def __enter__(self):
        self.logger.setLevel(self.new_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)


def log_exception(logger: logging.Logger, exception: Exception, 
                  message: str = "An error occurred") -> None:
    """
    Log an exception with full traceback
    
    Args:
        logger: Logger instance
        exception: Exception to log
        message: Additional context message
    """
    logger.error(f"{message}: {type(exception).__name__}: {str(exception)}", 
                 exc_info=True)


def create_scraping_log_entry(
    url: str,
    element_type: str,
    format_type: str,
    success: bool,
    error_message: Optional[str] = None,
    element_count: Optional[int] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a structured log entry for scraping operations
    
    Args:
        url: URL that was scraped
        element_type: Type of element extracted
        format_type: Output format
        success: Whether scraping was successful
        error_message: Error message if failed
        element_count: Number of elements extracted
        file_path: Path to saved file
        
    Returns:
        Structured log entry
    """
    from datetime import datetime
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'url': url,
        'element_type': element_type,
        'format_type': format_type,
        'success': success,
        'duration_seconds': None,  # To be calculated by caller
    }
    
    if success:
        entry['element_count'] = element_count
        entry['file_path'] = file_path
    else:
        entry['error'] = error_message
    
    return entry


# Create a default logger instance
logger = get_logger(__name__)