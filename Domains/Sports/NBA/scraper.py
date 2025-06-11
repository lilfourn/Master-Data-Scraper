"""
NBA scraper implementation

This module provides specialized scraping for NBA statistics
from various sources including NBA.com, Basketball Reference, and ESPN.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd
import logging
from urllib.parse import urljoin

from Domains.Sports.base import SportsScraper
from core.parser import HTMLParser
from utils.exceptions import ParsingError, NetworkError

logger = logging.getLogger(__name__)


class NBAScraper(SportsScraper):
    """NBA-specific scraper implementation"""
    
    def __init__(self):
        """Initialize NBA scraper"""
        super().__init__(sport='basketball', league='nba')
        
        # NBA-specific sources
        self.sources.update({
            'nba_official': 'https://www.nba.com/stats',
            'basketball_reference': 'https://www.basketball-reference.com',
            'espn_nba': 'https://www.espn.com/nba/stats',
            'cbs_nba': 'https://www.cbssports.com/nba/stats',
            'nba_stuffer': 'https://www.nbastuffer.com',
            'stat_muse': 'https://statmuse.com/nba'
        })
        
        # Team abbreviations mapping
        self.team_abbrevs = {
            'Atlanta Hawks': 'ATL',
            'Boston Celtics': 'BOS',
            'Brooklyn Nets': 'BKN',
            'Charlotte Hornets': 'CHA',
            'Chicago Bulls': 'CHI',
            'Cleveland Cavaliers': 'CLE',
            'Dallas Mavericks': 'DAL',
            'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET',
            'Golden State Warriors': 'GSW',
            'Houston Rockets': 'HOU',
            'Indiana Pacers': 'IND',
            'LA Clippers': 'LAC',
            'Los Angeles Lakers': 'LAL',
            'Memphis Grizzlies': 'MEM',
            'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL',
            'Minnesota Timberwolves': 'MIN',
            'New Orleans Pelicans': 'NOP',
            'New York Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC',
            'Orlando Magic': 'ORL',
            'Philadelphia 76ers': 'PHI',
            'Phoenix Suns': 'PHX',
            'Portland Trail Blazers': 'POR',
            'Sacramento Kings': 'SAC',
            'San Antonio Spurs': 'SAS',
            'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA',
            'Washington Wizards': 'WAS'
        }
    
    def get_standings(self, season: Optional[str] = None,
                     conference: Optional[str] = None) -> pd.DataFrame:
        """
        Get NBA standings
        
        Args:
            season: Season (e.g., '2023-24')
            conference: 'Eastern' or 'Western'
            
        Returns:
            DataFrame with standings
        """
        try:
            # Use Basketball Reference for reliable standings
            current_year = datetime.now().year
            if not season:
                # Determine current season based on month
                if datetime.now().month >= 10:  # Season starts in October
                    season = str(current_year + 1)
                else:
                    season = str(current_year)
            
            url = f"{self.sources['basketball_reference']}/leagues/NBA_{season}_standings.html"
            
            logger.info(f"Fetching NBA standings from {url}")
            
            # Scrape the page
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                # Basketball Reference returns consolidated standings
                standings = tables
                
                # Add metadata
                standings['Conference'] = 'NBA'  # Will be split later
                standings['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                standings['Season'] = season
                
                return standings
            
            # Fallback to ESPN
            return self._get_espn_standings(season, conference)
            
        except Exception as e:
            logger.error(f"Error getting NBA standings: {str(e)}")
            return pd.DataFrame()
    
    def _get_espn_standings(self, season: Optional[str] = None,
                           conference: Optional[str] = None) -> pd.DataFrame:
        """Get standings from ESPN as fallback"""
        try:
            url = self.sources['espn_nba']
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                # Add metadata
                tables['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                tables['Source'] = 'ESPN'
                
                return tables
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"ESPN standings fallback failed: {str(e)}")
            return pd.DataFrame()
    
    def get_scores(self, date: Optional[datetime] = None,
                  team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NBA game scores
        
        Args:
            date: Date for scores (defaults to today)
            team: Team filter
            
        Returns:
            DataFrame with scores
        """
        try:
            if not date:
                date = datetime.now()
            
            # Format date for URL
            date_str = date.strftime('%Y%m%d')
            
            # Use ESPN for scores
            url = f"https://www.espn.com/nba/scoreboard/_/date/{date_str}"
            
            logger.info(f"Fetching NBA scores for {date_str}")
            
            # Try to get scores table
            scores_data = self._parse_table(url)
            
            if scores_data is not None and not scores_data.empty:
                # Add date column
                scores_data['Date'] = date.strftime('%Y-%m-%d')
                
                # Filter by team if specified
                if team and not scores_data.empty:
                    # Look for team in any column that might contain team names
                    team_mask = False
                    for col in scores_data.columns:
                        if scores_data[col].dtype == 'object':
                            team_mask |= scores_data[col].str.contains(team, case=False, na=False)
                    
                    if hasattr(team_mask, '__iter__'):
                        scores_data = scores_data[team_mask]
                
                return scores_data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting NBA scores: {str(e)}")
            return pd.DataFrame()
    
    def get_player_stats(self, stat_type: str = 'season',
                        player: Optional[str] = None,
                        team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NBA player statistics
        
        Args:
            stat_type: 'season', 'career', or 'game'
            player: Player name filter
            team: Team filter
            
        Returns:
            DataFrame with player stats
        """
        try:
            # Use Basketball Reference for comprehensive stats
            current_year = datetime.now().year
            if datetime.now().month >= 10:
                season = current_year + 1
            else:
                season = current_year
                
            if stat_type == 'season':
                url = f"{self.sources['basketball_reference']}/leagues/NBA_{season}_per_game.html"
            else:
                url = f"{self.sources['basketball_reference']}/leagues/NBA_{season}_totals.html"
            
            logger.info(f"Fetching NBA player {stat_type} stats")
            
            stats_df = self._parse_table(url)
            
            if stats_df is not None and not stats_df.empty:
                # Filter by player if specified
                if player and 'Player' in stats_df.columns:
                    stats_df = stats_df[
                        stats_df['Player'].str.contains(player, case=False, na=False)
                    ]
                
                # Filter by team if specified
                if team and 'Tm' in stats_df.columns:
                    team_abbrev = self.team_abbrevs.get(team, team.upper())
                    stats_df = stats_df[
                        stats_df['Tm'] == team_abbrev
                    ]
                
                # Add metadata
                stats_df['Stat_Type'] = stat_type
                stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting player stats: {str(e)}")
            return pd.DataFrame()
    
    def get_team_stats(self, stat_type: str = 'season',
                      team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NBA team statistics
        
        Args:
            stat_type: 'season' or 'game'
            team: Team filter
            
        Returns:
            DataFrame with team stats
        """
        try:
            # Use ESPN for team stats
            url = self.sources['espn_nba']
            
            logger.info(f"Fetching NBA team {stat_type} stats")
            
            team_stats_df = self._parse_table(url)
            
            if team_stats_df is not None and not team_stats_df.empty:
                # Filter by team if specified
                if team:
                    # Look for team in any column
                    team_mask = False
                    for col in team_stats_df.columns:
                        if team_stats_df[col].dtype == 'object':
                            team_mask |= team_stats_df[col].str.contains(team, case=False, na=False)
                    
                    if hasattr(team_mask, '__iter__'):
                        team_stats_df = team_stats_df[team_mask]
                
                # Add metadata
                team_stats_df['Stat_Type'] = stat_type
                team_stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return team_stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting team stats: {str(e)}")
            return pd.DataFrame()
    
    def get_schedule(self, team: Optional[str] = None,
                    month: Optional[str] = None) -> pd.DataFrame:
        """Get NBA schedule"""
        try:
            if team:
                team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
                url = f"https://www.espn.com/nba/team/schedule/_/name/{team_abbrev}"
            else:
                url = "https://www.espn.com/nba/schedule"
            
            logger.info(f"Fetching NBA schedule")
            
            schedule_df = self._parse_table(url)
            
            if schedule_df is not None and not schedule_df.empty:
                # Add metadata
                schedule_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                # Filter by month if specified
                if month and 'Date' in schedule_df.columns:
                    schedule_df = schedule_df[
                        schedule_df['Date'].str.contains(month, case=False, na=False)
                    ]
                
                return schedule_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting schedule: {str(e)}")
            return pd.DataFrame()
    
    def get_roster(self, team: Optional[str] = None) -> pd.DataFrame:
        """Get NBA team roster"""
        try:
            if not team:
                logger.warning("Team name required for roster lookup")
                return pd.DataFrame()
                
            team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
            url = f"https://www.espn.com/nba/team/roster/_/name/{team_abbrev}"
            
            logger.info(f"Fetching roster for {team}")
            
            roster_df = self._parse_table(url)
            
            if roster_df is not None and not roster_df.empty:
                # Add team info
                roster_df['Team'] = team
                roster_df['Team_Abbrev'] = self.team_abbrevs.get(team, team.upper())
                roster_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return roster_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting roster: {str(e)}")
            return pd.DataFrame()
    
    def get_injuries(self) -> pd.DataFrame:
        """Get NBA injury report"""
        try:
            url = "https://www.espn.com/nba/injuries"
            
            logger.info("Fetching NBA injury report")
            
            injuries_df = self._parse_table(url)
            
            if injuries_df is not None and not injuries_df.empty:
                injuries_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return injuries_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting injury report: {str(e)}")
            return pd.DataFrame()
    
    def get_playoffs(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get NBA playoff bracket"""
        try:
            if not season:
                current_year = datetime.now().year
                if datetime.now().month >= 6:  # Playoffs end by June
                    season = str(current_year)
                else:
                    season = str(current_year - 1)
            
            url = f"{self.sources['basketball_reference']}/playoffs/NBA_{season}.html"
            
            logger.info(f"Fetching NBA playoff data for {season}")
            
            playoff_df = self._parse_table(url)
            
            if playoff_df is not None and not playoff_df.empty:
                playoff_df['Season'] = season
                playoff_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return playoff_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting playoff data: {str(e)}")
            return pd.DataFrame()