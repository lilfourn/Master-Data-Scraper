"""
Human behavior simulation for web scraping.

This module provides tools for mimicking human browsing patterns including:
- Random delay generation with human-like patterns
- Advanced exponential backoff strategies
- Request timing patterns that mimic human browsing
"""

import random
import time
import math
from typing import List, Tuple, Optional, Callable
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from enum import Enum


class BrowsingSpeed(Enum):
    """Enumeration of human browsing speeds."""
    VERY_SLOW = "very_slow"      # Careful reader
    SLOW = "slow"                 # Normal reader
    NORMAL = "normal"             # Average user
    FAST = "fast"                 # Quick scanner
    VERY_FAST = "very_fast"       # Power user


@dataclass
class HumanProfile:
    """Represents a human browsing profile."""
    speed: BrowsingSpeed
    attention_span: float  # 0.0 to 1.0
    curiosity: float      # 0.0 to 1.0
    fatigue_rate: float   # 0.0 to 1.0
    break_frequency: float  # 0.0 to 1.0
    
    @classmethod
    def generate_random(cls) -> 'HumanProfile':
        """Generate a random human profile."""
        return cls(
            speed=random.choice(list(BrowsingSpeed)),
            attention_span=random.uniform(0.3, 0.9),
            curiosity=random.uniform(0.2, 0.8),
            fatigue_rate=random.uniform(0.1, 0.5),
            break_frequency=random.uniform(0.1, 0.4)
        )


class HumanDelay:
    """Generates human-like delays for web scraping."""
    
    def __init__(self, profile: Optional[HumanProfile] = None):
        """
        Initialize HumanDelay with a browsing profile.
        
        Args:
            profile: Human browsing profile. If None, generates random profile.
        """
        self.profile = profile or HumanProfile.generate_random()
        self.session_start = datetime.now()
        self.request_count = 0
        self.last_request_time = None
        self.fatigue_level = 0.0
        
        # Speed multipliers
        self.speed_multipliers = {
            BrowsingSpeed.VERY_SLOW: 3.0,
            BrowsingSpeed.SLOW: 2.0,
            BrowsingSpeed.NORMAL: 1.0,
            BrowsingSpeed.FAST: 0.6,
            BrowsingSpeed.VERY_FAST: 0.3
        }
    
    def get_delay(self, base_delay: float = 1.0) -> float:
        """
        Get a human-like delay value.
        
        Args:
            base_delay: Base delay in seconds
            
        Returns:
            Delay time in seconds
        """
        # Apply speed multiplier
        speed_mult = self.speed_multipliers[self.profile.speed]
        
        # Add randomness using normal distribution
        # Humans don't have perfectly uniform timing
        mean_delay = base_delay * speed_mult
        std_dev = mean_delay * 0.3  # 30% standard deviation
        delay = np.random.normal(mean_delay, std_dev)
        
        # Ensure minimum delay
        delay = max(delay, 0.1)
        
        # Apply fatigue factor
        fatigue_mult = 1.0 + (self.fatigue_level * 2.0)
        delay *= fatigue_mult
        
        # Occasionally add "thinking time"
        if random.random() < 0.1:  # 10% chance
            thinking_time = random.uniform(2.0, 5.0) * speed_mult
            delay += thinking_time
        
        # Update fatigue
        self._update_fatigue()
        
        self.request_count += 1
        self.last_request_time = datetime.now()
        
        return delay
    
    def get_page_reading_delay(self, content_length: int) -> float:
        """
        Calculate delay based on content length (simulating reading time).
        
        Args:
            content_length: Length of content in characters
            
        Returns:
            Reading delay in seconds
        """
        # Average reading speed: 200-300 words per minute
        # Assuming 5 characters per word
        words = content_length / 5
        
        # Base reading speed (words per second)
        base_wps = 4.0  # 240 words per minute
        
        # Adjust for profile
        speed_mult = self.speed_multipliers[self.profile.speed]
        attention_mult = 0.5 + (self.profile.attention_span * 0.5)
        
        wps = base_wps / (speed_mult * attention_mult)
        reading_time = words / wps
        
        # Add scanning time (not everyone reads everything)
        if self.profile.attention_span < 0.5:
            reading_time *= 0.3  # Quick scan
        elif self.profile.attention_span < 0.7:
            reading_time *= 0.6  # Moderate reading
        
        # Add some randomness
        reading_time *= random.uniform(0.8, 1.2)
        
        # Cap maximum reading time
        return min(reading_time, 30.0)
    
    def get_mouse_movement_delay(self) -> float:
        """
        Simulate delay for mouse movement to element.
        
        Returns:
            Movement delay in seconds
        """
        base_movement = random.uniform(0.1, 0.5)
        speed_mult = self.speed_multipliers[self.profile.speed]
        
        # Add hesitation sometimes
        if random.random() < 0.2:
            hesitation = random.uniform(0.5, 1.5)
            base_movement += hesitation
        
        return base_movement * speed_mult
    
    def should_take_break(self) -> bool:
        """
        Determine if the human would take a break.
        
        Returns:
            True if should take break
        """
        # Check session duration
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # More likely to take breaks as session progresses
        session_factor = min(session_duration / 3600, 1.0)  # Max at 1 hour
        
        # Combine with profile and fatigue
        break_probability = (
            self.profile.break_frequency * 0.3 +
            self.fatigue_level * 0.4 +
            session_factor * 0.3
        )
        
        return random.random() < break_probability
    
    def get_break_duration(self) -> float:
        """
        Get duration for a break.
        
        Returns:
            Break duration in seconds
        """
        # Short break: 30s - 2min
        # Long break: 5min - 15min
        
        if random.random() < 0.7:  # 70% short breaks
            return random.uniform(30, 120)
        else:  # 30% long breaks
            return random.uniform(300, 900)
    
    def _update_fatigue(self):
        """Update fatigue level based on session activity."""
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # Fatigue increases over time
        time_fatigue = min(session_duration / 7200, 1.0)  # Max at 2 hours
        
        # Fatigue increases with request count
        request_fatigue = min(self.request_count / 200, 1.0)  # Max at 200 requests
        
        # Combine factors
        self.fatigue_level = (
            time_fatigue * 0.6 +
            request_fatigue * 0.4
        ) * self.profile.fatigue_rate
        
        # Cap fatigue
        self.fatigue_level = min(self.fatigue_level, 0.9)
    
    def reset_session(self):
        """Reset session data (simulating a fresh browsing session)."""
        self.session_start = datetime.now()
        self.request_count = 0
        self.last_request_time = None
        self.fatigue_level = 0.0


class BrowsingPattern:
    """Simulates different human browsing patterns."""
    
    def __init__(self, profile: Optional[HumanProfile] = None):
        """
        Initialize BrowsingPattern.
        
        Args:
            profile: Human browsing profile
        """
        self.profile = profile or HumanProfile.generate_random()
        self.visited_urls = []
        self.current_depth = 0
    
    def get_navigation_pattern(self) -> str:
        """
        Get the navigation pattern for current browsing.
        
        Returns:
            Pattern name
        """
        patterns = {
            'linear': 0.3,          # Page by page
            'depth_first': 0.25,    # Deep diving
            'breadth_first': 0.25,  # Scanning many pages
            'random': 0.2           # Random jumping
        }
        
        # Adjust based on curiosity
        if self.profile.curiosity > 0.7:
            patterns['depth_first'] += 0.1
            patterns['random'] += 0.1
            patterns['linear'] -= 0.2
        
        # Weighted random choice
        pattern_names = list(patterns.keys())
        weights = list(patterns.values())
        
        return random.choices(pattern_names, weights=weights)[0]
    
    def should_follow_link(self, link_text: str, link_position: int) -> bool:
        """
        Determine if a human would follow a specific link.
        
        Args:
            link_text: Text of the link
            link_position: Position of link on page (1-based)
            
        Returns:
            True if should follow link
        """
        # Base probability
        follow_prob = self.profile.curiosity
        
        # Position matters - links at top are more likely to be clicked
        position_factor = 1.0 / (1.0 + link_position * 0.1)
        follow_prob *= position_factor
        
        # Interesting keywords increase probability
        interesting_keywords = [
            'new', 'free', 'best', 'top', 'guide', 'how to',
            'tutorial', 'learn', 'exclusive', 'limited'
        ]
        
        link_lower = link_text.lower()
        for keyword in interesting_keywords:
            if keyword in link_lower:
                follow_prob *= 1.3
                break
        
        # Depth affects probability
        depth_factor = 1.0 / (1.0 + self.current_depth * 0.2)
        follow_prob *= depth_factor
        
        # Fatigue reduces link following
        follow_prob *= (1.0 - (self.profile.fatigue_rate * 0.5))
        
        return random.random() < min(follow_prob, 0.8)
    
    def get_scroll_pattern(self, page_height: int) -> List[Tuple[int, float]]:
        """
        Generate a human-like scroll pattern.
        
        Args:
            page_height: Total height of the page
            
        Returns:
            List of (scroll_position, delay) tuples
        """
        scroll_positions = []
        current_pos = 0
        
        while current_pos < page_height:
            # Determine scroll distance
            if self.profile.speed in [BrowsingSpeed.FAST, BrowsingSpeed.VERY_FAST]:
                # Fast scrollers make bigger jumps
                scroll_distance = random.randint(500, 1000)
            else:
                # Normal scrollers make smaller jumps
                scroll_distance = random.randint(200, 500)
            
            # Sometimes pause to read
            if random.random() < self.profile.attention_span:
                pause_duration = random.uniform(1.0, 5.0)
            else:
                pause_duration = random.uniform(0.2, 1.0)
            
            current_pos += scroll_distance
            current_pos = min(current_pos, page_height)
            
            scroll_positions.append((current_pos, pause_duration))
            
            # Occasionally scroll back up
            if random.random() < 0.1:
                back_distance = random.randint(100, 300)
                current_pos = max(0, current_pos - back_distance)
                scroll_positions.append((current_pos, random.uniform(0.5, 2.0)))
        
        return scroll_positions


class ExponentialBackoff:
    """Advanced exponential backoff strategy with jitter and human-like variations."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 300.0,
                 multiplier: float = 2.0, jitter: float = 0.3):
        """
        Initialize ExponentialBackoff.
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Delay multiplier for each retry
            jitter: Jitter factor (0.0 to 1.0)
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt = 0
        
    def get_delay(self) -> float:
        """
        Get the next backoff delay.
        
        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = min(
            self.base_delay * (self.multiplier ** self.attempt),
            self.max_delay
        )
        
        # Add jitter
        if self.jitter > 0:
            jitter_value = delay * self.jitter
            delay += random.uniform(-jitter_value, jitter_value)
        
        # Add human-like variation
        # Humans don't retry at exact intervals
        human_variation = random.uniform(0.8, 1.2)
        delay *= human_variation
        
        self.attempt += 1
        
        return max(delay, self.base_delay)
    
    def reset(self):
        """Reset the backoff state."""
        self.attempt = 0
    
    def get_decorrelated_delay(self) -> float:
        """
        Get delay using decorrelated jitter (recommended by AWS).
        
        Returns:
            Delay in seconds
        """
        if self.attempt == 0:
            delay = self.base_delay
        else:
            delay = min(
                self.max_delay,
                random.uniform(self.base_delay, self.base_delay * 3 * (self.multiplier ** (self.attempt - 1)))
            )
        
        self.attempt += 1
        return delay


class AdaptiveDelay:
    """Adaptive delay that adjusts based on server response times."""
    
    def __init__(self, target_rps: float = 1.0):
        """
        Initialize AdaptiveDelay.
        
        Args:
            target_rps: Target requests per second
        """
        self.target_rps = target_rps
        self.response_times = []
        self.window_size = 10
        self.min_delay = 0.5
        self.max_delay = 10.0
        
    def add_response_time(self, response_time: float):
        """
        Add a server response time observation.
        
        Args:
            response_time: Server response time in seconds
        """
        self.response_times.append(response_time)
        
        # Keep only recent observations
        if len(self.response_times) > self.window_size:
            self.response_times.pop(0)
    
    def get_delay(self) -> float:
        """
        Get adaptive delay based on server performance.
        
        Returns:
            Delay in seconds
        """
        base_delay = 1.0 / self.target_rps
        
        if not self.response_times:
            return base_delay
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / len(self.response_times)
        
        # If server is slow, increase delay
        if avg_response_time > 2.0:
            multiplier = min(avg_response_time / 2.0, 3.0)
            delay = base_delay * multiplier
        else:
            delay = base_delay
        
        # Add human-like variation
        delay *= random.uniform(0.8, 1.2)
        
        # Ensure within bounds
        return max(self.min_delay, min(delay, self.max_delay))


class RequestScheduler:
    """Schedules requests with human-like timing patterns."""
    
    def __init__(self, profile: Optional[HumanProfile] = None):
        """
        Initialize RequestScheduler.
        
        Args:
            profile: Human browsing profile
        """
        self.profile = profile or HumanProfile.generate_random()
        self.human_delay = HumanDelay(profile)
        self.browsing_pattern = BrowsingPattern(profile)
        self.backoff = ExponentialBackoff()
        self.adaptive_delay = AdaptiveDelay()
        
        # Time of day factors
        self.activity_patterns = {
            0: 0.1,   # Midnight
            1: 0.05,  # 1 AM
            2: 0.05,  # 2 AM
            3: 0.05,  # 3 AM
            4: 0.1,   # 4 AM
            5: 0.2,   # 5 AM
            6: 0.4,   # 6 AM
            7: 0.6,   # 7 AM
            8: 0.8,   # 8 AM
            9: 1.0,   # 9 AM
            10: 1.0,  # 10 AM
            11: 1.0,  # 11 AM
            12: 0.9,  # Noon
            13: 0.8,  # 1 PM
            14: 0.9,  # 2 PM
            15: 1.0,  # 3 PM
            16: 1.0,  # 4 PM
            17: 0.9,  # 5 PM
            18: 0.8,  # 6 PM
            19: 0.9,  # 7 PM
            20: 1.0,  # 8 PM
            21: 0.9,  # 9 PM
            22: 0.7,  # 10 PM
            23: 0.4   # 11 PM
        }
    
    def get_next_request_time(self, failed: bool = False) -> float:
        """
        Get the delay until the next request.
        
        Args:
            failed: Whether the last request failed
            
        Returns:
            Delay in seconds
        """
        if failed:
            # Use exponential backoff for failures
            delay = self.backoff.get_delay()
        else:
            # Reset backoff on success
            self.backoff.reset()
            
            # Get base human delay
            delay = self.human_delay.get_delay()
            
            # Apply time of day factor
            current_hour = datetime.now().hour
            time_factor = self.activity_patterns.get(current_hour, 0.5)
            delay /= time_factor  # Less active times = longer delays
        
        # Check if should take break
        if self.human_delay.should_take_break():
            break_duration = self.human_delay.get_break_duration()
            delay += break_duration
            # Reset session after break
            self.human_delay.reset_session()
        
        return delay
    
    def simulate_burst_pattern(self, num_requests: int) -> List[float]:
        """
        Generate delays for a burst of requests (like loading a page with resources).
        
        Args:
            num_requests: Number of requests in burst
            
        Returns:
            List of delays
        """
        delays = []
        
        # First request has normal delay
        delays.append(self.human_delay.get_delay())
        
        # Subsequent requests happen quickly (parallel loading)
        for i in range(1, num_requests):
            # Small delays between burst requests
            burst_delay = random.uniform(0.05, 0.2)
            delays.append(burst_delay)
        
        return delays