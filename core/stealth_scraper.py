"""
Stealth Web Scraper - Advanced scraper with anti-detection features

This module provides a specialized scraper for sites with strong
anti-bot protection, using all available stealth techniques.
"""

import logging
import random
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
import yaml

from .web_scraper import WebScraper
from utils.stealth import UserAgentRotator, HeaderGenerator, StealthSession
from utils.human_behavior import HumanDelay, RequestScheduler, AdaptiveDelay
from utils.rate_limiter import RateLimiter
from config import get_settings

logger = logging.getLogger(__name__)


class StealthWebScraper(WebScraper):
    """
    Advanced web scraper with comprehensive anti-detection features
    
    This scraper implements:
    - User agent rotation
    - Human-like browsing patterns
    - Advanced rate limit handling
    - Browser fingerprinting
    - Session persistence
    """
    
    def __init__(self, stealth_config_path: Optional[Path] = None, **kwargs):
        """
        Initialize stealth scraper
        
        Args:
            stealth_config_path: Path to stealth configuration file
            **kwargs: Additional arguments for WebScraper
        """
        # Load stealth configuration
        self.stealth_config = self._load_stealth_config(stealth_config_path)
        
        # Initialize stealth components if enabled
        if self.stealth_config['stealth']['enabled']:
            self._init_stealth_components()
        else:
            self.ua_rotator = None
            self.header_gen = None
            self.human_delay = None
            self.stealth_session = None
            self.request_scheduler = None
            self.adaptive_delay = None
        
        # Initialize base scraper
        super().__init__(**kwargs)
        
        # Override user agent if stealth is enabled
        if self.ua_rotator and self.stealth_config.get('stealth', {}).get('user_agent_rotation', {}).get('enabled', True):
            self.user_agent = self.ua_rotator.get_random_user_agent()
            self.session.headers['User-Agent'] = self.user_agent
        
        # Request tracking for rotation
        self.request_count = 0
        self.domain_request_counts = {}
        
    def _load_stealth_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load stealth configuration"""
        if not config_path:
            config_path = Path("config/stealth.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Return default configuration
            return {
                'stealth': {'enabled': True},
                'human_behavior': {'enabled': True},
                'rate_limit_handling': {}
            }
    
    def _init_stealth_components(self):
        """Initialize stealth components"""
        # User agent rotation
        self.ua_rotator = UserAgentRotator()
        self.header_gen = HeaderGenerator()
        
        # Human behavior simulation
        behavior_config = self.stealth_config.get('human_behavior', {})
        if behavior_config.get('enabled', True):
            self.human_delay = HumanDelay(
                profile=None  # Will generate a random profile
            )
            self.request_scheduler = RequestScheduler()
            # Calculate target RPS from min_delay (delay = 1/rps)
            min_delay = behavior_config.get('delays', {}).get('min_delay', 1.0)
            target_rps = 1.0 / min_delay if min_delay > 0 else 1.0
            self.adaptive_delay = AdaptiveDelay(
                target_rps=target_rps
            )
        else:
            self.human_delay = None
            self.request_scheduler = None
            self.adaptive_delay = None
        
        # Stealth session
        self.stealth_session = StealthSession()
    
    def _should_rotate_ua(self) -> bool:
        """Check if user agent should be rotated"""
        if not self.stealth_config['stealth']['user_agent_rotation']['enabled']:
            return False
        
        rotate_after = self.stealth_config['stealth']['user_agent_rotation']['rotate_after_requests']
        return self.request_count % rotate_after == 0
    
    def _apply_human_delay(self, url: str, response: Optional[Any] = None):
        """Apply human-like delay before request"""
        if not self.human_delay:
            return
        
        # Get domain-specific settings
        domain = self.validator.extract_domain(url)
        domain_config = self.stealth_config.get('rate_limit_handling', {}).get(
            'domain_specific', {}
        ).get(domain, {})
        
        # Calculate base delay
        if response and hasattr(response, 'text'):
            # Get content length from response
            content_length = len(response.text)
            delay = self.human_delay.get_page_reading_delay(content_length)
        else:
            delay = self.human_delay.get_delay()  # Use base delay method
        
        # Apply domain-specific adjustments
        if domain_config:
            min_delay = domain_config.get('min_delay', 1.0)
            max_delay = domain_config.get('max_delay', 5.0)
            delay = max(min_delay, min(delay, max_delay))
        
        # Add break probability
        break_prob = domain_config.get('break_probability', 
                                     self.stealth_config['human_behavior']['breaks']['short_break_probability'])
        if random.random() < break_prob:
            break_min, break_max = self.stealth_config['human_behavior']['breaks']['short_break_duration']
            delay += random.uniform(break_min, break_max)
            logger.info(f"Taking a short break ({delay:.1f}s)")
        
        # Check for long break
        domain_requests = self.domain_request_counts.get(domain, 0)
        long_break_after = self.stealth_config['human_behavior']['breaks']['long_break_after_requests']
        if domain_requests > 0 and domain_requests % long_break_after == 0:
            break_min, break_max = self.stealth_config['human_behavior']['breaks']['long_break_duration']
            break_time = random.uniform(break_min, break_max)
            logger.info(f"Taking a long break ({break_time:.1f}s) after {domain_requests} requests to {domain}")
            time.sleep(break_time)
        
        # Apply the delay
        if delay > 0:
            logger.debug(f"Waiting {delay:.1f}s (human-like delay)")
            time.sleep(delay)
    
    def _update_headers_for_request(self, url: str, headers: Dict[str, str]) -> Dict[str, str]:
        """Update headers for stealth"""
        if not self.header_gen:
            return headers
        
        # Generate browser-like headers
        stealth_headers = self.header_gen.generate_headers(
            user_agent=self.user_agent,
            referer=self.last_url if hasattr(self, 'last_url') else None
        )
        
        # Merge with existing headers
        headers.update(stealth_headers)
        
        # Apply configuration options
        header_config = self.stealth_config['stealth']['headers']
        if header_config.get('randomize_accept_language'):
            headers['Accept-Language'] = self._random_accept_language()
        
        if header_config.get('include_dnt'):
            headers['DNT'] = '1'
        
        return headers
    
    def _get_browser_from_ua(self, user_agent: str) -> str:
        """Extract browser type from user agent"""
        ua_lower = user_agent.lower()
        if 'chrome' in ua_lower and 'edg' not in ua_lower:
            return 'chrome'
        elif 'firefox' in ua_lower:
            return 'firefox'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            return 'safari'
        elif 'edg' in ua_lower:
            return 'edge'
        else:
            return 'chrome'  # Default
    
    def _random_accept_language(self) -> str:
        """Generate random Accept-Language header"""
        languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-US,en;q=0.9,fr;q=0.8',
            'en-US,en;q=0.9,de;q=0.8',
            'en-CA,en;q=0.9',
            'en-AU,en;q=0.9',
        ]
        return random.choice(languages)
    
    def fetch(self, url: str, method: str = "GET", use_cache: bool = True, **kwargs) -> Any:
        """
        Fetch URL with stealth features
        
        Adds:
        - Human-like delays
        - Header randomization
        - User agent rotation
        - Advanced rate limit handling
        """
        # Track requests
        self.request_count += 1
        domain = self.validator.extract_domain(url)
        self.domain_request_counts[domain] = self.domain_request_counts.get(domain, 0) + 1
        
        # Rotate user agent if needed
        if self._should_rotate_ua():
            old_ua = self.user_agent
            self.user_agent = self.ua_rotator.get_random()
            self.session.headers['User-Agent'] = self.user_agent
            logger.debug(f"Rotated user agent from {old_ua[:30]}... to {self.user_agent[:30]}...")
        
        # Update headers for stealth
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers'] = self._update_headers_for_request(url, kwargs['headers'])
        
        # Apply human delay (before request)
        self._apply_human_delay(url)
        
        # Track timing for adaptive delays
        start_time = time.time()
        
        try:
            # Make request with parent class
            response = super().fetch(url, method, use_cache, **kwargs)
            
            # Update adaptive delay based on response time
            if self.adaptive_delay:
                response_time = time.time() - start_time
                self.adaptive_delay.add_response_time(response_time)
            
            # Store last URL for referer chain
            self.last_url = url
            
            return response
            
        except Exception as e:
            # Handle rate limits with extra stealth
            if "429" in str(e) or "rate limit" in str(e).lower():
                logger.warning(f"Rate limited on {domain}, applying stealth tactics")
                
                # Always rotate user agent after rate limit
                if self.ua_rotator:
                    self.user_agent = self.ua_rotator.get_random()
                    self.session.headers['User-Agent'] = self.user_agent
                
                # Take a longer break
                break_time = random.uniform(30, 60)
                logger.info(f"Taking extended break ({break_time:.1f}s) after rate limit")
                time.sleep(break_time)
            
            raise
    
    def scrape(self, url: str, element_type: str, **kwargs) -> Any:
        """
        Scrape with stealth features
        
        Adds request scheduling and pattern simulation
        """
        # Check if we should make this request based on schedule
        if self.request_scheduler:
            wait_time = self.request_scheduler.get_next_request_time()
            if wait_time > 0:
                logger.info(f"Request scheduler suggests waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
        # Perform scraping
        result = super().scrape(url, element_type, **kwargs)
        
        # Simulate browsing patterns
        if self.stealth_config['human_behavior']['patterns']['follow_links_probability'] > 0:
            # Randomly decide to "explore" related pages (just log, don't actually visit)
            if random.random() < self.stealth_config['human_behavior']['patterns']['follow_links_probability']:
                logger.debug("Human behavior: Would explore related links")
        
        return result
    
    def get_stealth_stats(self) -> Dict[str, Any]:
        """Get statistics about stealth operations"""
        stats = {
            'total_requests': self.request_count,
            'domains_visited': len(self.domain_request_counts),
            'current_user_agent': self.user_agent[:50] + '...' if len(self.user_agent) > 50 else self.user_agent,
            'domain_requests': dict(self.domain_request_counts),
            'stealth_enabled': self.stealth_config['stealth']['enabled'],
            'human_behavior_enabled': self.stealth_config['human_behavior']['enabled']
        }
        
        if self.adaptive_delay and self.adaptive_delay.response_times:
            stats['average_response_time'] = sum(self.adaptive_delay.response_times) / len(self.adaptive_delay.response_times)
            stats['current_delay'] = self.adaptive_delay.get_delay()
        
        return stats


class StealthCrawler(StealthWebScraper):
    """
    Stealth crawler that combines crawling with anti-detection
    
    Perfect for crawling sites with aggressive anti-bot measures
    """
    
    def crawl_with_stealth(self, start_url: str, **kwargs) -> Dict[str, Any]:
        """
        Crawl website with full stealth features
        
        Implements:
        - Pattern-based crawling (depth-first, breadth-first, random)
        - Human-like link following
        - Domain-specific strategies
        """
        # Get crawl pattern
        patterns = self.stealth_config['human_behavior']['patterns']
        
        # Adjust max_depth with variance
        if 'max_depth' in kwargs:
            variance = patterns.get('max_depth_variance', 0)
            if variance > 0:
                kwargs['max_depth'] += random.randint(-variance, variance)
                kwargs['max_depth'] = max(1, kwargs['max_depth'])  # Ensure positive
        
        # Use fast crawl with stealth features already integrated
        return self.fast_crawl_and_scrape(start_url, **kwargs)