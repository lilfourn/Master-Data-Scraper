"""
User-Agent rotation module for web scraping

This module provides user-agent rotation functionality to help
avoid detection and blocking during web scraping.
"""

import random
from typing import List, Optional, Dict
from fake_useragent import UserAgent
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class UserAgentRotator:
    """
    Manages a pool of user agents for rotation
    """
    
    # Default user agents for different browsers
    DEFAULT_USER_AGENTS = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Chrome on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        
        # Firefox on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15) Gecko/20100101 Firefox/119.0",
        
        # Safari on Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    ]
    
    def __init__(self, 
                 user_agents: Optional[List[str]] = None,
                 use_fake_useragent: bool = True,
                 fallback_to_default: bool = True,
                 browsers: Optional[List[str]] = None):
        """
        Initialize user agent rotator
        
        Args:
            user_agents: Custom list of user agents
            use_fake_useragent: Whether to use fake-useragent library
            fallback_to_default: Whether to fallback to default user agents
            browsers: List of browsers to get agents for (chrome, firefox, safari, edge)
        """
        self.custom_agents = user_agents or []
        self.use_fake_useragent = use_fake_useragent
        self.fallback_to_default = fallback_to_default
        self.browsers = browsers or ['chrome', 'firefox', 'safari', 'edge']
        
        self._user_agents: List[str] = []
        self._fake_ua: Optional[UserAgent] = None
        self._lock = Lock()
        
        # Initialize user agent pool
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the user agent pool"""
        with self._lock:
            # Start with custom agents
            self._user_agents = self.custom_agents.copy()
            
            # Add fake-useragent agents if enabled
            if self.use_fake_useragent:
                try:
                    self._fake_ua = UserAgent()
                    
                    # Add agents for specified browsers
                    for browser in self.browsers:
                        try:
                            # Get multiple agents per browser
                            for _ in range(3):
                                if browser == 'chrome':
                                    agent = self._fake_ua.chrome
                                elif browser == 'firefox':
                                    agent = self._fake_ua.firefox
                                elif browser == 'safari':
                                    agent = self._fake_ua.safari
                                elif browser == 'edge':
                                    agent = self._fake_ua.edge
                                else:
                                    continue
                                
                                if agent and agent not in self._user_agents:
                                    self._user_agents.append(agent)
                        except Exception:
                            # Individual browser might fail
                            pass
                    
                    logger.info(f"Loaded {len(self._user_agents)} user agents from fake-useragent")
                    
                except Exception as e:
                    logger.warning(f"Failed to initialize fake-useragent: {str(e)}")
                    self._fake_ua = None
            
            # Fallback to default agents if needed
            if self.fallback_to_default and len(self._user_agents) < 5:
                for agent in self.DEFAULT_USER_AGENTS:
                    if agent not in self._user_agents:
                        self._user_agents.append(agent)
                logger.info(f"Added default user agents, total: {len(self._user_agents)}")
            
            if not self._user_agents:
                # Last resort - add at least one agent
                self._user_agents = ["MasterDataScraper/1.0"]
                logger.warning("No user agents available, using default bot user agent")
    
    def get_random(self) -> str:
        """
        Get a random user agent from the pool
        
        Returns:
            Random user agent string
        """
        with self._lock:
            if not self._user_agents:
                self._initialize_pool()
            
            return random.choice(self._user_agents)
    
    def get_specific_browser(self, browser: str) -> str:
        """
        Get a user agent for a specific browser
        
        Args:
            browser: Browser name (chrome, firefox, safari, edge)
            
        Returns:
            User agent string for the specified browser
        """
        browser = browser.lower()
        
        # Try fake-useragent first
        if self._fake_ua:
            try:
                if browser == 'chrome':
                    return self._fake_ua.chrome
                elif browser == 'firefox':
                    return self._fake_ua.firefox
                elif browser == 'safari':
                    return self._fake_ua.safari
                elif browser == 'edge':
                    return self._fake_ua.edge
            except Exception:
                pass
        
        # Fallback to filtering from pool
        with self._lock:
            browser_agents = [
                agent for agent in self._user_agents
                if browser in agent.lower()
            ]
            
            if browser_agents:
                return random.choice(browser_agents)
            
            # Last resort
            return self.get_random()
    
    def add_custom_agent(self, user_agent: str) -> None:
        """
        Add a custom user agent to the pool
        
        Args:
            user_agent: User agent string to add
        """
        with self._lock:
            if user_agent not in self._user_agents:
                self._user_agents.append(user_agent)
                logger.debug(f"Added custom user agent: {user_agent[:50]}...")
    
    def remove_agent(self, user_agent: str) -> bool:
        """
        Remove a user agent from the pool
        
        Args:
            user_agent: User agent string to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if user_agent in self._user_agents and len(self._user_agents) > 1:
                self._user_agents.remove(user_agent)
                logger.debug(f"Removed user agent: {user_agent[:50]}...")
                return True
            return False
    
    def get_all_agents(self) -> List[str]:
        """
        Get all user agents in the pool
        
        Returns:
            List of all user agent strings
        """
        with self._lock:
            return self._user_agents.copy()
    
    def get_pool_size(self) -> int:
        """
        Get the size of the user agent pool
        
        Returns:
            Number of user agents in the pool
        """
        with self._lock:
            return len(self._user_agents)
    
    def reset_pool(self) -> None:
        """Reset the user agent pool to initial state"""
        with self._lock:
            self._user_agents.clear()
            self._initialize_pool()
        logger.info("User agent pool reset")


class UserAgentMiddleware:
    """
    Middleware to automatically rotate user agents for requests
    """
    
    def __init__(self, rotator: Optional[UserAgentRotator] = None,
                 rotate_on_each_request: bool = True,
                 sticky_domains: bool = False):
        """
        Initialize user agent middleware
        
        Args:
            rotator: UserAgentRotator instance
            rotate_on_each_request: Whether to rotate on each request
            sticky_domains: Whether to use same agent for same domain
        """
        self.rotator = rotator or UserAgentRotator()
        self.rotate_on_each_request = rotate_on_each_request
        self.sticky_domains = sticky_domains
        
        self._domain_agents: Dict[str, str] = {}
        self._current_agent = self.rotator.get_random()
        self._lock = Lock()
    
    def get_user_agent(self, url: Optional[str] = None) -> str:
        """
        Get user agent for a request
        
        Args:
            url: Optional URL to get agent for
            
        Returns:
            User agent string
        """
        if not self.rotate_on_each_request and not self.sticky_domains:
            return self._current_agent
        
        if self.sticky_domains and url:
            # Extract domain from URL
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            
            with self._lock:
                # Check if we have a sticky agent for this domain
                if domain in self._domain_agents:
                    return self._domain_agents[domain]
                
                # Assign new agent for this domain
                agent = self.rotator.get_random()
                self._domain_agents[domain] = agent
                return agent
        
        # Rotate on each request
        if self.rotate_on_each_request:
            with self._lock:
                self._current_agent = self.rotator.get_random()
        
        return self._current_agent
    
    def process_request(self, request_headers: Dict[str, str], 
                       url: Optional[str] = None) -> Dict[str, str]:
        """
        Process request headers to add/update user agent
        
        Args:
            request_headers: Request headers dictionary
            url: Optional URL for the request
            
        Returns:
            Updated headers dictionary
        """
        headers = request_headers.copy()
        headers['User-Agent'] = self.get_user_agent(url)
        return headers
    
    def clear_domain_cache(self) -> None:
        """Clear the domain-specific user agent cache"""
        with self._lock:
            self._domain_agents.clear()
        logger.debug("Cleared domain user agent cache")


# Convenience functions
def get_random_user_agent() -> str:
    """
    Get a random user agent string
    
    Returns:
        Random user agent
    """
    rotator = UserAgentRotator()
    return rotator.get_random()


def create_rotating_session(session=None, rotator: Optional[UserAgentRotator] = None):
    """
    Create or modify a requests session with user agent rotation
    
    Args:
        session: Existing requests session or None to create new
        rotator: UserAgentRotator instance
        
    Returns:
        Modified requests session
    """
    import requests
    
    if session is None:
        session = requests.Session()
    
    if rotator is None:
        rotator = UserAgentRotator()
    
    # Store original request method
    original_request = session.request
    
    def rotating_request(method, url, **kwargs):
        # Update user agent header
        headers = kwargs.get('headers', {})
        headers['User-Agent'] = rotator.get_random()
        kwargs['headers'] = headers
        
        # Make request with rotated user agent
        return original_request(method, url, **kwargs)
    
    # Replace request method
    session.request = rotating_request
    
    return session