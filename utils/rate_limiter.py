"""
Rate limiting module for ethical web scraping

This module provides rate limiting functionality to ensure
responsible scraping practices.
"""

import time
from collections import defaultdict
from typing import Optional, Dict, Callable
from functools import wraps
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for controlling request frequency
    
    Implements per-domain rate limiting with configurable delays
    """
    
    def __init__(self, 
                 default_delay: float = 1.0,
                 domain_delays: Optional[Dict[str, float]] = None):
        """
        Initialize rate limiter
        
        Args:
            default_delay: Default delay between requests (seconds)
            domain_delays: Custom delays for specific domains
        """
        self.default_delay = default_delay
        self.domain_delays = domain_delays or {}
        self.last_request_time = defaultdict(float)
        self.lock = Lock()
    
    def get_delay_for_domain(self, domain: str) -> float:
        """
        Get delay for a specific domain
        
        Args:
            domain: Domain name
            
        Returns:
            Delay in seconds
        """
        return self.domain_delays.get(domain, self.default_delay)
    
    def wait_if_needed(self, domain: str) -> float:
        """
        Wait if necessary to respect rate limit
        
        Args:
            domain: Domain being accessed
            
        Returns:
            Actual wait time in seconds
        """
        with self.lock:
            current_time = time.time()
            last_request = self.last_request_time[domain]
            required_delay = self.get_delay_for_domain(domain)
            
            time_since_last = current_time - last_request
            
            if time_since_last < required_delay:
                wait_time = required_delay - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                time.sleep(wait_time)
                self.last_request_time[domain] = time.time()
                return wait_time
            else:
                self.last_request_time[domain] = current_time
                return 0
    
    def update_domain_delay(self, domain: str, delay: float) -> None:
        """
        Update delay for a specific domain
        
        Args:
            domain: Domain name
            delay: New delay in seconds
        """
        self.domain_delays[domain] = delay
        logger.info(f"Updated rate limit for {domain}: {delay}s")
    
    def reset(self, domain: Optional[str] = None) -> None:
        """
        Reset rate limit tracking
        
        Args:
            domain: Specific domain to reset, or None for all
        """
        with self.lock:
            if domain:
                self.last_request_time.pop(domain, None)
            else:
                self.last_request_time.clear()


def rate_limit(delay: float = 1.0):
    """
    Decorator for rate-limiting functions
    
    Args:
        delay: Delay in seconds between calls
        
    Returns:
        Decorated function
    """
    last_called = [0]
    lock = Lock()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()
                time_since_last = current_time - last_called[0]
                
                if time_since_last < delay:
                    wait_time = delay - time_since_last
                    time.sleep(wait_time)
                
                last_called[0] = time.time()
                
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class RequestQueue:
    """
    Queue for managing concurrent requests with rate limiting
    """
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize request queue
        
        Args:
            max_concurrent: Maximum concurrent requests
            rate_limiter: RateLimiter instance to use
        """
        self.max_concurrent = max_concurrent
        self.rate_limiter = rate_limiter or RateLimiter()
        self.active_requests = 0
        self.lock = Lock()
    
    def acquire(self, domain: str) -> None:
        """
        Acquire permission to make a request
        
        Args:
            domain: Domain for the request
        """
        # Wait for rate limit
        self.rate_limiter.wait_if_needed(domain)
        
        # Wait for concurrent limit
        while True:
            with self.lock:
                if self.active_requests < self.max_concurrent:
                    self.active_requests += 1
                    break
            time.sleep(0.1)
    
    def release(self) -> None:
        """Release a request slot"""
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts delays based on response codes
    """
    
    def __init__(self, 
                 default_delay: float = 1.0,
                 min_delay: float = 0.5,
                 max_delay: float = 10.0,
                 backoff_factor: float = 2.0):
        """
        Initialize adaptive rate limiter
        
        Args:
            default_delay: Starting delay
            min_delay: Minimum allowed delay
            max_delay: Maximum allowed delay
            backoff_factor: Multiplier for increasing delay
        """
        super().__init__(default_delay)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.success_count = defaultdict(int)
        self.error_count = defaultdict(int)
    
    def record_success(self, domain: str) -> None:
        """
        Record successful request and potentially decrease delay
        
        Args:
            domain: Domain of successful request
        """
        with self.lock:
            self.success_count[domain] += 1
            self.error_count[domain] = 0
            
            # Decrease delay after consecutive successes
            if self.success_count[domain] >= 5:
                current_delay = self.get_delay_for_domain(domain)
                new_delay = max(self.min_delay, current_delay * 0.9)
                self.update_domain_delay(domain, new_delay)
                self.success_count[domain] = 0
    
    def record_error(self, domain: str, status_code: Optional[int] = None) -> None:
        """
        Record failed request and increase delay
        
        Args:
            domain: Domain of failed request
            status_code: HTTP status code
        """
        with self.lock:
            self.error_count[domain] += 1
            self.success_count[domain] = 0
            
            # Increase delay for rate limit errors
            if status_code == 429 or self.error_count[domain] >= 3:
                current_delay = self.get_delay_for_domain(domain)
                new_delay = min(self.max_delay, current_delay * self.backoff_factor)
                self.update_domain_delay(domain, new_delay)
                self.error_count[domain] = 0