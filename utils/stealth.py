"""
Stealth utilities for web scraping to avoid detection.

This module provides tools for mimicking real browser behavior including:
- User-Agent rotation with realistic browser/OS combinations
- Realistic header generation that matches User-Agent
- Browser fingerprint randomization utilities
"""

import random
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import yaml
import os
from pathlib import Path


class UserAgentRotator:
    """Manages rotation of user agents with realistic browser/OS combinations."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the UserAgentRotator.
        
        Args:
            config_path: Path to user agents YAML config. Defaults to config/user_agents.yaml
        """
        self.config_path = config_path or os.path.join(
            Path(__file__).parent.parent, 'config', 'user_agents.yaml'
        )
        self.user_agents = self._load_user_agents()
        self._last_used_index = -1
        
    def _load_user_agents(self) -> Dict[str, List[str]]:
        """Load user agents from YAML configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default user agents if config not found
            return self._get_default_user_agents()
    
    def _get_default_user_agents(self) -> Dict[str, List[str]]:
        """Return default user agents if config file not found."""
        return {
            'chrome_windows': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            ],
            'firefox_windows': [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
            ],
            'safari_mac': [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
            ]
        }
    
    def get_random_user_agent(self, category: Optional[str] = None) -> str:
        """
        Get a random user agent string.
        
        Args:
            category: Specific category (e.g., 'chrome_windows', 'mobile')
                     If None, selects from all categories
        
        Returns:
            Random user agent string
        """
        if category and category in self.user_agents:
            agents = self.user_agents[category]
        else:
            # Flatten all user agents
            agents = []
            for agent_list in self.user_agents.values():
                agents.extend(agent_list)
        
        if not agents:
            # Fallback to a default Chrome user agent
            return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Avoid using the same user agent consecutively
        if len(agents) > 1:
            index = random.randint(0, len(agents) - 1)
            while index == self._last_used_index and len(agents) > 1:
                index = random.randint(0, len(agents) - 1)
            self._last_used_index = index
            return agents[index]
        
        return agents[0]
    
    def get_weighted_random_user_agent(self) -> str:
        """
        Get a weighted random user agent (more likely to get popular browsers).
        
        Returns:
            Weighted random user agent string
        """
        # Weight distribution (adjust as needed)
        weights = {
            'chrome_windows': 40,
            'chrome_mac': 15,
            'firefox_windows': 15,
            'firefox_mac': 5,
            'safari_mac': 15,
            'edge_windows': 8,
            'mobile': 2
        }
        
        categories = []
        for category, weight in weights.items():
            if category in self.user_agents:
                categories.extend([category] * weight)
        
        if categories:
            selected_category = random.choice(categories)
            return self.get_random_user_agent(selected_category)
        
        return self.get_random_user_agent()


class HeaderGenerator:
    """Generates realistic HTTP headers that match the User-Agent."""
    
    def __init__(self):
        """Initialize the HeaderGenerator."""
        self.common_languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-US,en;q=0.9,fr;q=0.8',
            'en-US,en;q=0.9,de;q=0.8',
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7'
        ]
        
        self.common_encodings = [
            'gzip, deflate, br',
            'gzip, deflate',
            'gzip, deflate, br, zstd'
        ]
    
    def generate_headers(self, user_agent: str, referer: Optional[str] = None,
                        origin: Optional[str] = None) -> Dict[str, str]:
        """
        Generate realistic headers based on user agent.
        
        Args:
            user_agent: The user agent string
            referer: Optional referer URL
            origin: Optional origin URL
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            'User-Agent': user_agent,
            'Accept-Language': random.choice(self.common_languages),
            'Accept-Encoding': random.choice(self.common_encodings),
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # Detect browser type from user agent
        browser_type = self._detect_browser_type(user_agent)
        
        # Add browser-specific headers
        if browser_type == 'chrome':
            headers.update(self._get_chrome_headers())
        elif browser_type == 'firefox':
            headers.update(self._get_firefox_headers())
        elif browser_type == 'safari':
            headers.update(self._get_safari_headers())
        elif browser_type == 'edge':
            headers.update(self._get_edge_headers())
        
        # Add optional headers
        if referer:
            headers['Referer'] = referer
        
        if origin:
            headers['Origin'] = origin
        
        # Randomly add some optional headers
        if random.random() > 0.5:
            headers['DNT'] = '1'
        
        if random.random() > 0.7:
            headers['Upgrade-Insecure-Requests'] = '1'
        
        return headers
    
    def _detect_browser_type(self, user_agent: str) -> str:
        """Detect browser type from user agent string."""
        user_agent_lower = user_agent.lower()
        
        if 'edg/' in user_agent_lower:
            return 'edge'
        elif 'chrome' in user_agent_lower and 'safari' in user_agent_lower:
            return 'chrome'
        elif 'firefox' in user_agent_lower:
            return 'firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return 'safari'
        else:
            return 'chrome'  # Default to Chrome
    
    def _get_chrome_headers(self) -> Dict[str, str]:
        """Get Chrome-specific headers."""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
        # Randomly vary sec-ch-ua values
        if random.random() > 0.5:
            headers['Sec-Ch-Ua-Platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
        
        return headers
    
    def _get_firefox_headers(self) -> Dict[str, str]:
        """Get Firefox-specific headers."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
    
    def _get_safari_headers(self) -> Dict[str, str]:
        """Get Safari-specific headers."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    
    def _get_edge_headers(self) -> Dict[str, str]:
        """Get Edge-specific headers."""
        headers = self._get_chrome_headers()
        headers['Sec-Ch-Ua'] = '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"'
        return headers


class BrowserFingerprint:
    """Utilities for randomizing browser fingerprints."""
    
    def __init__(self):
        """Initialize BrowserFingerprint."""
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (2560, 1440), (3840, 2160),
            (1920, 1200), (2560, 1600), (1680, 1050), (1280, 1024)
        ]
        
        self.color_depths = [24, 32]
        
        self.timezones = [
            'America/New_York', 'America/Chicago', 'America/Los_Angeles',
            'America/Denver', 'Europe/London', 'Europe/Paris',
            'Asia/Tokyo', 'Asia/Shanghai', 'Australia/Sydney'
        ]
        
        self.plugins = [
            'Chrome PDF Plugin', 'Chrome PDF Viewer', 'Native Client',
            'Shockwave Flash', 'Widevine Content Decryption Module'
        ]
        
        self.webgl_vendors = [
            'Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple Inc.',
            'Google Inc.', 'ARM', 'Qualcomm'
        ]
        
        self.webgl_renderers = [
            'Intel(R) HD Graphics', 'NVIDIA GeForce GTX',
            'AMD Radeon', 'Apple GPU', 'Mali-G', 'Adreno'
        ]
    
    def generate_fingerprint(self) -> Dict[str, any]:
        """
        Generate a random browser fingerprint.
        
        Returns:
            Dictionary containing fingerprint data
        """
        screen_res = random.choice(self.screen_resolutions)
        available_res = (
            screen_res[0] - random.randint(0, 100),
            screen_res[1] - random.randint(50, 150)
        )
        
        fingerprint = {
            'screen_resolution': screen_res,
            'available_screen_resolution': available_res,
            'color_depth': random.choice(self.color_depths),
            'timezone': random.choice(self.timezones),
            'timezone_offset': self._get_timezone_offset(),
            'session_storage': True,
            'local_storage': True,
            'indexed_db': True,
            'webgl_vendor': random.choice(self.webgl_vendors),
            'webgl_renderer': self._get_matching_renderer(),
            'cpu_cores': random.choice([2, 4, 6, 8, 12, 16]),
            'memory': random.choice([2, 4, 8, 16, 32]),
            'languages': self._generate_languages(),
            'platform': self._get_platform(),
            'plugins': self._generate_plugins(),
            'canvas_fingerprint': self._generate_canvas_fingerprint(),
            'audio_fingerprint': self._generate_audio_fingerprint(),
            'font_list': self._generate_font_list(),
            'do_not_track': random.choice([True, False, None]),
            'hardware_concurrency': random.choice([2, 4, 8, 16]),
            'device_pixel_ratio': random.choice([1, 1.25, 1.5, 2, 3])
        }
        
        return fingerprint
    
    def _get_timezone_offset(self) -> int:
        """Get timezone offset in minutes."""
        offsets = {
            'America/New_York': -300,
            'America/Chicago': -360,
            'America/Los_Angeles': -480,
            'America/Denver': -420,
            'Europe/London': 0,
            'Europe/Paris': 60,
            'Asia/Tokyo': 540,
            'Asia/Shanghai': 480,
            'Australia/Sydney': 660
        }
        return random.choice(list(offsets.values()))
    
    def _get_matching_renderer(self) -> str:
        """Get a renderer that matches the vendor."""
        renderers = {
            'Intel Inc.': ['Intel(R) HD Graphics 620', 'Intel(R) UHD Graphics 630'],
            'NVIDIA Corporation': ['NVIDIA GeForce GTX 1060', 'NVIDIA GeForce RTX 3070'],
            'AMD': ['AMD Radeon RX 580', 'AMD Radeon RX 6700 XT'],
            'Apple Inc.': ['Apple M1', 'Apple M2'],
        }
        vendor = random.choice(list(renderers.keys()))
        return random.choice(renderers[vendor])
    
    def _generate_languages(self) -> List[str]:
        """Generate language preferences."""
        language_sets = [
            ['en-US', 'en'],
            ['en-GB', 'en'],
            ['en-US', 'en', 'es'],
            ['en-US', 'en', 'fr'],
            ['de-DE', 'de', 'en'],
            ['fr-FR', 'fr', 'en']
        ]
        return random.choice(language_sets)
    
    def _get_platform(self) -> str:
        """Get platform string."""
        platforms = ['Win32', 'MacIntel', 'Linux x86_64', 'Linux i686']
        return random.choice(platforms)
    
    def _generate_plugins(self) -> List[str]:
        """Generate plugin list."""
        num_plugins = random.randint(0, len(self.plugins))
        return random.sample(self.plugins, num_plugins)
    
    def _generate_canvas_fingerprint(self) -> str:
        """Generate a fake canvas fingerprint."""
        # Generate a random hash-like string
        return ''.join(random.choices('0123456789abcdef', k=32))
    
    def _generate_audio_fingerprint(self) -> float:
        """Generate a fake audio fingerprint."""
        return round(random.uniform(0.00001, 0.00009), 8)
    
    def _generate_font_list(self) -> List[str]:
        """Generate a list of installed fonts."""
        common_fonts = [
            'Arial', 'Arial Black', 'Comic Sans MS', 'Courier New',
            'Georgia', 'Impact', 'Times New Roman', 'Trebuchet MS',
            'Verdana', 'Helvetica', 'Helvetica Neue', 'Calibri',
            'Cambria', 'Consolas', 'Tahoma', 'Segoe UI'
        ]
        num_fonts = random.randint(10, len(common_fonts))
        return random.sample(common_fonts, num_fonts)


class StealthSession:
    """Manages a stealthy browsing session with consistent fingerprint."""
    
    def __init__(self):
        """Initialize a stealth session."""
        self.user_agent_rotator = UserAgentRotator()
        self.header_generator = HeaderGenerator()
        self.fingerprint_generator = BrowserFingerprint()
        
        # Generate consistent session data
        self.user_agent = self.user_agent_rotator.get_weighted_random_user_agent()
        self.fingerprint = self.fingerprint_generator.generate_fingerprint()
        self.session_id = self._generate_session_id()
        
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid
        return str(uuid.uuid4())
    
    def get_headers(self, url: str, referer: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for a request to the given URL.
        
        Args:
            url: Target URL
            referer: Optional referer URL
            
        Returns:
            Dictionary of headers
        """
        # Extract origin from URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        
        headers = self.header_generator.generate_headers(
            self.user_agent,
            referer=referer,
            origin=origin if referer else None
        )
        
        # Add session-specific headers
        headers['Accept-Encoding'] = 'gzip, deflate, br'
        
        return headers
    
    def rotate_user_agent(self):
        """Rotate to a new user agent while maintaining session consistency."""
        self.user_agent = self.user_agent_rotator.get_weighted_random_user_agent()
    
    def get_fingerprint_js(self) -> str:
        """
        Get JavaScript code to override browser fingerprint.
        
        Returns:
            JavaScript code string
        """
        fp = self.fingerprint
        
        js_code = f"""
        // Override screen properties
        Object.defineProperty(screen, 'width', {{value: {fp['screen_resolution'][0]}, writable: false}});
        Object.defineProperty(screen, 'height', {{value: {fp['screen_resolution'][1]}, writable: false}});
        Object.defineProperty(screen, 'availWidth', {{value: {fp['available_screen_resolution'][0]}, writable: false}});
        Object.defineProperty(screen, 'availHeight', {{value: {fp['available_screen_resolution'][1]}, writable: false}});
        Object.defineProperty(screen, 'colorDepth', {{value: {fp['color_depth']}, writable: false}});
        Object.defineProperty(screen, 'pixelDepth', {{value: {fp['color_depth']}, writable: false}});
        
        // Override navigator properties
        Object.defineProperty(navigator, 'userAgent', {{value: '{self.user_agent}', writable: false}});
        Object.defineProperty(navigator, 'platform', {{value: '{fp['platform']}', writable: false}});
        Object.defineProperty(navigator, 'languages', {{value: {fp['languages']}, writable: false}});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{value: {fp['hardware_concurrency']}, writable: false}});
        Object.defineProperty(navigator, 'deviceMemory', {{value: {fp['memory']}, writable: false}});
        
        // Override timezone
        Date.prototype.getTimezoneOffset = function() {{ return {fp['timezone_offset']}; }};
        
        // Override WebGL
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{fp['webgl_vendor']}';
            if (parameter === 37446) return '{fp['webgl_renderer']}';
            return getParameter.apply(this, arguments);
        }};
        """
        
        return js_code