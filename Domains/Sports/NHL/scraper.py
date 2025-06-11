"""
NHL scraper implementation

This module provides specialized scraping for NHL statistics
from various sources including NHL.com, Hockey Reference, and ESPN.
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


class NHLScraper(SportsScraper):
    """NHL-specific scraper implementation"""
    
    def __init__(self):
        """Initialize NHL scraper"""
        super().__init__(sport='hockey', league='nhl')
        
        # NHL-specific sources
        self.sources.update({
            'nhl_official': 'https://www.nhl.com/stats',
            'hockey_reference': 'https://www.hockey-reference.com',
            'espn_nhl': 'https://www.espn.com/nhl/stats',
            'cbs_nhl': 'https://www.cbssports.com/nhl/stats',
            'natural_stat_trick': 'https://www.naturalstattrick.com',
            'moneypuck': 'https://moneypuck.com'
        })
        
        # Team abbreviations mapping
        self.team_abbrevs = {
            'Anaheim Ducks': 'ANA',
            'Arizona Coyotes': 'ARI',
            'Boston Bruins': 'BOS',
            'Buffalo Sabres': 'BUF',
            'Calgary Flames': 'CGY',
            'Carolina Hurricanes': 'CAR',
            'Chicago Blackhawks': 'CHI',
            'Colorado Avalanche': 'COL',
            'Columbus Blue Jackets': 'CBJ',
            'Dallas Stars': 'DAL',
            'Detroit Red Wings': 'DET',
            'Edmonton Oilers': 'EDM',
            'Florida Panthers': 'FLA',
            'Los Angeles Kings': 'LAK',
            'Minnesota Wild': 'MIN',
            'Montreal Canadiens': 'MTL',
            'Nashville Predators': 'NSH',
            'New Jersey Devils': 'NJD',
            'New York Islanders': 'NYI',
            'New York Rangers': 'NYR',
            'Ottawa Senators': 'OTT',
            'Philadelphia Flyers': 'PHI',
            'Pittsburgh Penguins': 'PIT',
            'San Jose Sharks': 'SJS',
            'Seattle Kraken': 'SEA',
            'St. Louis Blues': 'STL',
            'Tampa Bay Lightning': 'TBL',
            'Toronto Maple Leafs': 'TOR',
            'Vancouver Canucks': 'VAN',
            'Vegas Golden Knights': 'VGK',
            'Washington Capitals': 'WSH',
            'Winnipeg Jets': 'WPG'
        }
    
    def get_standings(self, season: Optional[str] = None,
                     conference: Optional[str] = None) -> pd.DataFrame:
        """
        Get NHL standings
        
        Args:
            season: Season (e.g., '2023-24')
            conference: 'Eastern' or 'Western'
            
        Returns:
            DataFrame with standings
        """
        try:
            # Use ESPN for standings
            url = self.sources['espn_nhl']
            
            logger.info(f"Fetching NHL standings from {url}")
            
            # Scrape the page
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                standings = tables
                
                # Add metadata
                standings['Conference'] = conference or 'NHL'
                standings['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                standings['Season'] = season or self._get_current_season()
                
                return standings
            
            # Try Hockey Reference as fallback
            return self._get_hockey_ref_standings(season)
            
        except Exception as e:
            logger.error(f"Error getting NHL standings: {str(e)}")
            return pd.DataFrame()
    
    def _get_current_season(self) -> str:
        """Get current NHL season string"""
        now = datetime.now()
        # NHL season runs from October to June
        if now.month >= 10:
            return f"{now.year}-{str(now.year + 1)[2:]}"
        else:
            return f"{now.year - 1}-{str(now.year)[2:]}"
    
    def _get_hockey_ref_standings(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get standings from Hockey Reference"""
        try:
            if not season:
                season = self._get_current_season()
            year = season.split('-')[1]
            if len(year) == 2:
                year = '20' + year
            
            url = f"{self.sources['hockey_reference']}/leagues/NHL_{year}_standings.html"
            
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                # Add metadata
                tables['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                tables['Source'] = 'Hockey Reference'
                tables['Season'] = season
                
                return tables
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Hockey Reference standings fallback failed: {str(e)}")
            return pd.DataFrame()
    
    def get_scores(self, date: Optional[datetime] = None,
                  team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NHL game scores
        
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
            url = f"https://www.espn.com/nhl/scoreboard/_/date/{date_str}"
            
            logger.info(f"Fetching NHL scores for {date_str}")
            
            # Try to get scores table
            scores_data = self._parse_table(url)
            
            if scores_data is not None and not scores_data.empty:
                # Add date column
                scores_data['Date'] = date.strftime('%Y-%m-%d')
                
                # Filter by team if specified
                if team and not scores_data.empty:
                    # Look for team in any column
                    team_mask = False
                    for col in scores_data.columns:
                        if scores_data[col].dtype == 'object':
                            team_mask |= scores_data[col].str.contains(team, case=False, na=False)
                    
                    if hasattr(team_mask, '__iter__'):
                        scores_data = scores_data[team_mask]
                
                return scores_data
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting NHL scores: {str(e)}")
            return pd.DataFrame()
    
    def get_player_stats(self, stat_type: str = 'season',
                        player: Optional[str] = None,
                        team: Optional[str] = None,
                        position: Optional[str] = None) -> pd.DataFrame:
        """
        Get NHL player statistics
        
        Args:
            stat_type: 'season', 'career', or 'game'
            player: Player name filter
            team: Team filter
            position: Position filter (C, LW, RW, D, G)
            
        Returns:
            DataFrame with player stats
        """
        try:
            # Use Hockey Reference for comprehensive stats
            season = self._get_current_season()
            year = season.split('-')[1]
            if len(year) == 2:
                year = '20' + year
            
            # Different URLs for different stat types
            if position and position.upper() == 'G':
                url = f"{self.sources['hockey_reference']}/leagues/NHL_{year}_goalies.html"
            else:
                url = f"{self.sources['hockey_reference']}/leagues/NHL_{year}_skaters.html"
            
            logger.info(f"Fetching NHL player {stat_type} stats")
            
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
                
                # Filter by position if specified
                if position and 'Pos' in stats_df.columns:
                    stats_df = stats_df[
                        stats_df['Pos'].str.contains(position.upper(), na=False)
                    ]
                
                # Add metadata
                stats_df['Stat_Type'] = stat_type
                stats_df['Season'] = season
                stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting player stats: {str(e)}")
            return pd.DataFrame()
    
    def get_team_stats(self, stat_type: str = 'season',
                      team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NHL team statistics
        
        Args:
            stat_type: 'season' or 'game'
            team: Team filter
            
        Returns:
            DataFrame with team stats
        """
        try:
            # Use ESPN for team stats
            url = self.sources['espn_nhl']
            
            logger.info(f"Fetching NHL team {stat_type} stats")
            
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
                team_stats_df['Season'] = self._get_current_season()
                team_stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return team_stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting team stats: {str(e)}")
            return pd.DataFrame()
    
    def get_schedule(self, team: Optional[str] = None,
                    month: Optional[str] = None) -> pd.DataFrame:
        """Get NHL schedule"""
        try:
            if team:
                team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
                url = f"https://www.espn.com/nhl/team/schedule/_/name/{team_abbrev}"
            else:
                url = "https://www.espn.com/nhl/schedule"
            
            logger.info(f"Fetching NHL schedule")
            
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
        """Get NHL team roster"""
        try:
            if not team:
                logger.warning("Team name required for roster lookup")
                return pd.DataFrame()
                
            team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
            url = f"https://www.espn.com/nhl/team/roster/_/name/{team_abbrev}"
            
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
        """Get NHL injury report"""
        try:
            url = "https://www.espn.com/nhl/injuries"
            
            logger.info("Fetching NHL injury report")
            
            injuries_df = self._parse_table(url)
            
            if injuries_df is not None and not injuries_df.empty:
                injuries_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return injuries_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting injury report: {str(e)}")
            return pd.DataFrame()
    
    def get_playoffs(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get NHL playoff bracket"""
        try:
            if not season:
                season = self._get_current_season()
            
            year = season.split('-')[1]
            if len(year) == 2:
                year = '20' + year
            
            url = f"{self.sources['hockey_reference']}/playoffs/NHL_{year}.html"
            
            logger.info(f"Fetching NHL playoff data for {season}")
            
            playoff_df = self._parse_table(url)
            
            if playoff_df is not None and not playoff_df.empty:
                playoff_df['Season'] = season
                playoff_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return playoff_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting playoff data: {str(e)}")
            return pd.DataFrame()
    
    def get_draft_picks(self, year: Optional[int] = None,
                       team: Optional[str] = None,
                       round: Optional[int] = None) -> pd.DataFrame:
        """
        Get NHL draft picks
        
        Args:
            year: Draft year
            team: Team filter
            round: Round filter
            
        Returns:
            DataFrame with draft picks
        """
        try:
            if not year:
                year = datetime.now().year
            
            url = f"{self.sources['hockey_reference']}/draft/NHL_{year}_entry.html"
            
            logger.info(f"Fetching NHL draft picks for {year}")
            
            draft_df = self._parse_table(url)
            
            if draft_df is not None and not draft_df.empty:
                # Filter by team if specified
                if team and 'Team' in draft_df.columns:
                    draft_df = draft_df[
                        draft_df['Team'].str.contains(team, case=False, na=False)
                    ]
                
                # Filter by round if specified
                if round and 'Rd' in draft_df.columns:
                    draft_df = draft_df[draft_df['Rd'] == str(round)]
                
                # Add metadata
                draft_df['Draft_Year'] = year
                draft_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return draft_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting draft picks: {str(e)}")
            return pd.DataFrame()