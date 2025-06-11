"""
WNBA scraper implementation

This module provides specialized scraping for WNBA statistics
from various sources including WNBA.com, Basketball Reference, and ESPN.
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


class WNBAScraper(SportsScraper):
    """WNBA-specific scraper implementation"""
    
    def __init__(self):
        """Initialize WNBA scraper"""
        super().__init__(sport='basketball', league='wnba')
        
        # WNBA-specific sources
        self.sources.update({
            'wnba_official': 'https://www.wnba.com/stats',
            'basketball_reference': 'https://www.basketball-reference.com/wnba/',
            'espn_wnba': 'https://www.espn.com/wnba/stats',
            'cbs_wnba': 'https://www.cbssports.com/wnba/stats',
            'her_hoop_stats': 'https://www.herhoopstats.com',
            'stats_wnba': 'https://stats.wnba.com'
        })
        
        # Team abbreviations mapping
        self.team_abbrevs = {
            'Atlanta Dream': 'ATL',
            'Chicago Sky': 'CHI',
            'Connecticut Sun': 'CON',
            'Dallas Wings': 'DAL',
            'Indiana Fever': 'IND',
            'Las Vegas Aces': 'LV',
            'Los Angeles Sparks': 'LA',
            'Minnesota Lynx': 'MIN',
            'New York Liberty': 'NY',
            'Phoenix Mercury': 'PHX',
            'Seattle Storm': 'SEA',
            'Washington Mystics': 'WAS'
        }
    
    def get_standings(self, season: Optional[str] = None,
                     conference: Optional[str] = None) -> pd.DataFrame:
        """
        Get WNBA standings
        
        Args:
            season: Season year (e.g., '2024')
            conference: 'Eastern' or 'Western' (WNBA has conferences)
            
        Returns:
            DataFrame with standings
        """
        try:
            # Use ESPN for standings
            url = self.sources['espn_wnba']
            
            logger.info(f"Fetching WNBA standings from {url}")
            
            # Scrape the page
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                standings = tables
                
                # Add metadata
                standings['Conference'] = conference or 'WNBA'
                standings['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                standings['Season'] = season or str(datetime.now().year)
                
                return standings
            
            # Try Basketball Reference as fallback
            return self._get_bbref_standings(season)
            
        except Exception as e:
            logger.error(f"Error getting WNBA standings: {str(e)}")
            return pd.DataFrame()
    
    def _get_bbref_standings(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get standings from Basketball Reference"""
        try:
            year = season or str(datetime.now().year)
            url = f"{self.sources['basketball_reference']}years/WNBA_{year}_standings.html"
            
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                # Add metadata
                tables['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                tables['Source'] = 'Basketball Reference'
                tables['Season'] = year
                
                return tables
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Basketball Reference standings fallback failed: {str(e)}")
            return pd.DataFrame()
    
    def get_scores(self, date: Optional[datetime] = None,
                  team: Optional[str] = None) -> pd.DataFrame:
        """
        Get WNBA game scores
        
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
            url = f"https://www.espn.com/wnba/scoreboard/_/date/{date_str}"
            
            logger.info(f"Fetching WNBA scores for {date_str}")
            
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
            logger.error(f"Error getting WNBA scores: {str(e)}")
            return pd.DataFrame()
    
    def get_player_stats(self, stat_type: str = 'season',
                        player: Optional[str] = None,
                        team: Optional[str] = None) -> pd.DataFrame:
        """
        Get WNBA player statistics
        
        Args:
            stat_type: 'season', 'career', or 'game'
            player: Player name filter
            team: Team filter
            
        Returns:
            DataFrame with player stats
        """
        try:
            # Use Basketball Reference for comprehensive stats
            year = datetime.now().year
            
            if stat_type == 'season':
                url = f"{self.sources['basketball_reference']}years/WNBA_{year}_per_game.html"
            else:
                url = f"{self.sources['basketball_reference']}years/WNBA_{year}_totals.html"
            
            logger.info(f"Fetching WNBA player {stat_type} stats")
            
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
                stats_df['Season'] = year
                stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting player stats: {str(e)}")
            return pd.DataFrame()
    
    def get_team_stats(self, stat_type: str = 'season',
                      team: Optional[str] = None) -> pd.DataFrame:
        """
        Get WNBA team statistics
        
        Args:
            stat_type: 'season' or 'game'
            team: Team filter
            
        Returns:
            DataFrame with team stats
        """
        try:
            # Use ESPN for team stats
            url = self.sources['espn_wnba']
            
            logger.info(f"Fetching WNBA team {stat_type} stats")
            
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
                team_stats_df['Season'] = datetime.now().year
                team_stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return team_stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting team stats: {str(e)}")
            return pd.DataFrame()
    
    def get_schedule(self, team: Optional[str] = None,
                    month: Optional[str] = None) -> pd.DataFrame:
        """Get WNBA schedule"""
        try:
            if team:
                team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
                url = f"https://www.espn.com/wnba/team/schedule/_/name/{team_abbrev}"
            else:
                url = "https://www.espn.com/wnba/schedule"
            
            logger.info(f"Fetching WNBA schedule")
            
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
        """Get WNBA team roster"""
        try:
            if not team:
                logger.warning("Team name required for roster lookup")
                return pd.DataFrame()
                
            team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
            url = f"https://www.espn.com/wnba/team/roster/_/name/{team_abbrev}"
            
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
        """Get WNBA injury report"""
        try:
            url = "https://www.espn.com/wnba/injuries"
            
            logger.info("Fetching WNBA injury report")
            
            injuries_df = self._parse_table(url)
            
            if injuries_df is not None and not injuries_df.empty:
                injuries_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return injuries_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting injury report: {str(e)}")
            return pd.DataFrame()
    
    def get_playoffs(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get WNBA playoff bracket"""
        try:
            if not season:
                # WNBA season runs from May to October
                current_year = datetime.now().year
                if datetime.now().month >= 10:
                    season = str(current_year)
                else:
                    season = str(current_year)
            
            url = f"{self.sources['basketball_reference']}years/WNBA_{season}_playoffs.html"
            
            logger.info(f"Fetching WNBA playoff data for {season}")
            
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
        Get WNBA draft picks
        
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
            
            url = f"{self.sources['basketball_reference']}draft/WNBA_{year}.html"
            
            logger.info(f"Fetching WNBA draft picks for {year}")
            
            draft_df = self._parse_table(url)
            
            if draft_df is not None and not draft_df.empty:
                # Filter by team if specified
                if team and 'Tm' in draft_df.columns:
                    team_abbrev = self.team_abbrevs.get(team, team.upper())
                    draft_df = draft_df[draft_df['Tm'] == team_abbrev]
                
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
    
    def get_all_star_game(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        Get WNBA All-Star Game data (WNBA-specific method)
        
        Args:
            year: Year of All-Star game
            
        Returns:
            DataFrame with All-Star game data
        """
        try:
            if not year:
                year = datetime.now().year
            
            url = f"{self.sources['basketball_reference']}allstar/WNBA_{year}.html"
            
            logger.info(f"Fetching WNBA All-Star Game data for {year}")
            
            allstar_df = self._parse_table(url)
            
            if allstar_df is not None and not allstar_df.empty:
                allstar_df['Year'] = year
                allstar_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return allstar_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting All-Star game data: {str(e)}")
            return pd.DataFrame()