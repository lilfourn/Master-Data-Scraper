"""
Base class for sports domain scrapers

This module provides the foundation for all sports scrapers with
common functionality for standings, scores, and stats extraction.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import pandas as pd
import json
import logging

from core.web_scraper import WebScraper
from core.parser import HTMLParser
from core.exporter import CSVExporter, JSONExporter, MarkdownExporter
from core.validator import InputValidator
from utils.rate_limiter import RateLimiter
from utils.exceptions import ScraperException, NetworkError, ParsingError

logger = logging.getLogger(__name__)


class SportsScraper(ABC):
    """Base class for all sports domain scrapers"""
    
    # Common data types across all sports
    DATA_TYPES = [
        'standings',
        'scores', 
        'player_stats',
        'team_stats',
        'schedules',
        'rosters',
        'injuries',
        'playoffs'
    ]
    
    # Default sources that most sports will have
    DEFAULT_SOURCES = {
        'espn': 'https://www.espn.com/{sport}/stats',
        'cbs': 'https://www.cbssports.com/{sport}/stats',
        'fox': 'https://www.foxsports.com/{sport}/stats'
    }
    
    def __init__(self, sport: str, league: str):
        """
        Initialize sports scraper
        
        Args:
            sport: Sport name (e.g., 'basketball', 'football', 'hockey')
            league: League name (e.g., 'nba', 'nfl', 'nhl', 'wnba')
        """
        self.sport = sport.lower()
        self.league = league.upper()
        self.scraper = WebScraper()
        self.validator = InputValidator()
        # Create a custom organizer without logs directory
        self.data_dir = Path(f"Data/Domains/Sports/{self.league}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Sport-specific sources (to be defined by subclasses)
        self.sources = self._get_default_sources()
        
        # Data cache for the session
        self.data_cache = {}
        
        # Initialize exporters
        self.exporters = {
            'csv': CSVExporter(),
            'json': JSONExporter(),
            'md': MarkdownExporter()
        }
    
    def _get_default_sources(self) -> Dict[str, str]:
        """Get default sources with sport filled in"""
        sources = {}
        for name, url_template in self.DEFAULT_SOURCES.items():
            sources[name] = url_template.format(sport=self.sport)
        return sources
    
    @abstractmethod
    def get_standings(self, season: Optional[str] = None, 
                     conference: Optional[str] = None) -> pd.DataFrame:
        """
        Get current standings
        
        Args:
            season: Season year (e.g., '2023-24')
            conference: Conference filter (e.g., 'Eastern', 'Western')
            
        Returns:
            DataFrame with standings data
        """
        pass
    
    @abstractmethod
    def get_scores(self, date: Optional[datetime] = None,
                  team: Optional[str] = None) -> pd.DataFrame:
        """
        Get game scores
        
        Args:
            date: Date to get scores for
            team: Team filter
            
        Returns:
            DataFrame with scores data
        """
        pass
    
    @abstractmethod
    def get_player_stats(self, stat_type: str = 'season',
                        player: Optional[str] = None,
                        team: Optional[str] = None) -> pd.DataFrame:
        """
        Get player statistics
        
        Args:
            stat_type: Type of stats ('season', 'career', 'game')
            player: Player name filter
            team: Team filter
            
        Returns:
            DataFrame with player stats
        """
        pass
    
    @abstractmethod
    def get_team_stats(self, stat_type: str = 'season',
                      team: Optional[str] = None) -> pd.DataFrame:
        """
        Get team statistics
        
        Args:
            stat_type: Type of stats ('season', 'game')
            team: Team filter
            
        Returns:
            DataFrame with team stats
        """
        pass
    
    def scrape_all(self, data_types: Optional[List[str]] = None,
                  export_format: str = 'csv') -> Dict[str, Any]:
        """
        Scrape all requested data types
        
        Args:
            data_types: List of data types to scrape
            export_format: Format to export data in
            
        Returns:
            Dictionary with file paths for each data type
        """
        if not data_types:
            data_types = ['standings', 'scores', 'player_stats', 'team_stats']
        
        results = {}
        
        for data_type in data_types:
            try:
                logger.info(f"Scraping {data_type} for {self.league}")
                
                # Get the appropriate method
                method_map = {
                    'standings': self.get_standings,
                    'scores': self.get_scores,
                    'player_stats': self.get_player_stats,
                    'team_stats': self.get_team_stats,
                    'schedule': self.get_schedule,
                    'roster': lambda: self.get_roster() if hasattr(self, 'get_roster') else pd.DataFrame(),
                    'injuries': self.get_injuries,
                    'playoffs': self.get_playoffs
                }
                
                if data_type not in method_map:
                    logger.warning(f"Unknown data type: {data_type}")
                    continue
                
                # Scrape the data
                data = method_map[data_type]()
                
                # Save the data
                if data is not None and not data.empty:
                    filename = self._generate_filename(data_type, export_format)
                    filepath = self._save_data(data, filename, export_format)
                    results[data_type] = filepath
                    logger.info(f"Saved {data_type} to {filepath}")
                else:
                    logger.warning(f"No data found for {data_type}")
                    
            except Exception as e:
                logger.error(f"Error scraping {data_type}: {str(e)}")
                results[data_type] = None
        
        return results
    
    def _generate_filename(self, data_type: str, format_type: str) -> str:
        """Generate filename for scraped data"""
        timestamp = datetime.now().strftime('%Y-%m-%d')
        return f"{self.league}_{data_type}_{timestamp}.{format_type}"
    
    def _save_data(self, data: pd.DataFrame, filename: str, 
                   format_type: str) -> Path:
        """Save data to file"""
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.data_dir / filename
        
        if format_type in self.exporters:
            self.exporters[format_type].export(data, filepath)
        else:
            # Default to CSV
            data.to_csv(filepath, index=False)
        
        return filepath
    
    def _parse_table(self, url: str, table_selector: str = 'table',
                    table_index: int = 0) -> Optional[pd.DataFrame]:
        """
        Parse a table from a URL
        
        Args:
            url: URL to scrape
            table_selector: CSS selector for table
            table_index: Index of table if multiple exist
            
        Returns:
            DataFrame or None if parsing fails
        """
        try:
            # Validate URL
            is_valid, validated_url = self.validator.validate_url(url, check_accessibility=False)
            if not is_valid:
                logger.error(f"Invalid URL: {url}")
                return None
            
            # Scrape the page
            scraped_data = self.scraper.scrape(
                url=validated_url,
                element_type='table',
                save=False
            )
            
            if scraped_data and isinstance(scraped_data, list) and len(scraped_data) > table_index:
                return scraped_data[table_index]
            elif scraped_data and isinstance(scraped_data, pd.DataFrame):
                return scraped_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing table from {url}: {str(e)}")
            return None
    
    def _normalize_team_name(self, team: str) -> str:
        """Normalize team name for consistency"""
        # Remove common prefixes/suffixes
        team = team.strip()
        team = team.replace('FC', '').strip()
        team = team.replace('HC', '').strip()
        
        # Handle city/name splits
        parts = team.split()
        if len(parts) > 1:
            # Keep last part as primary identifier
            return parts[-1]
        
        return team
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%d %b %Y',
            '%B %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def get_schedule(self, team: Optional[str] = None,
                    month: Optional[str] = None) -> pd.DataFrame:
        """
        Get game schedule
        
        Args:
            team: Team filter
            month: Month filter
            
        Returns:
            DataFrame with schedule data
        """
        # Default implementation - can be overridden
        logger.warning(f"Schedule scraping not implemented for {self.league}")
        return pd.DataFrame()
    
    def get_roster(self, team: Optional[str] = None) -> pd.DataFrame:
        """
        Get team roster
        
        Args:
            team: Team name (if None, gets all teams)
            
        Returns:
            DataFrame with roster data
        """
        # Default implementation - can be overridden
        logger.warning(f"Roster scraping not implemented for {self.league}")
        return pd.DataFrame()
    
    def get_injuries(self) -> pd.DataFrame:
        """
        Get injury report
        
        Returns:
            DataFrame with injury data
        """
        # Default implementation - can be overridden
        logger.warning(f"Injury report scraping not implemented for {self.league}")
        return pd.DataFrame()
    
    def get_playoffs(self, season: Optional[str] = None) -> pd.DataFrame:
        """
        Get playoff bracket/results
        
        Args:
            season: Season year
            
        Returns:
            DataFrame with playoff data
        """
        # Default implementation - can be overridden
        logger.warning(f"Playoff scraping not implemented for {self.league}")
        return pd.DataFrame()
    
    @property
    def available_sources(self) -> List[str]:
        """Get list of available data sources"""
        return list(self.sources.keys())
    
    def add_source(self, name: str, url: str) -> None:
        """Add a custom data source"""
        self.sources[name] = url
        logger.info(f"Added source '{name}' for {self.league}")
    
    def clear_cache(self) -> None:
        """Clear data cache"""
        self.data_cache.clear()
        logger.info(f"Cleared data cache for {self.league}")
        
    def save_metadata(self, data_type: str, metadata: Dict[str, Any]) -> None:
        """Save metadata about scraped data"""
        metadata_file = self.data_dir / f"{self.league}_{data_type}_metadata.json"
        
        # Add timestamp and league info
        metadata.update({
            'league': self.league,
            'sport': self.sport,
            'data_type': data_type,
            'scraped_at': datetime.now().isoformat(),
            'sources': self.sources
        })
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved metadata for {data_type} to {metadata_file}")