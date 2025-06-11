"""
NFL scraper implementation

This module provides specialized scraping for NFL statistics
from various sources including NFL.com, Pro Football Reference, and ESPN.
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


class NFLScraper(SportsScraper):
    """NFL-specific scraper implementation"""
    
    def __init__(self):
        """Initialize NFL scraper"""
        super().__init__(sport='football', league='nfl')
        
        # NFL-specific sources
        self.sources.update({
            'nfl_official': 'https://www.nfl.com/stats/',
            'pro_football_reference': 'https://www.pro-football-reference.com',
            'espn_nfl': 'https://www.espn.com/nfl/stats',
            'cbs_nfl': 'https://www.cbssports.com/nfl/stats',
            'fox_nfl': 'https://www.foxsports.com/nfl/stats',
            'nfl_savant': 'https://www.nflsavant.com'
        })
        
        # Team abbreviations mapping
        self.team_abbrevs = {
            'Arizona Cardinals': 'ARI',
            'Atlanta Falcons': 'ATL',
            'Baltimore Ravens': 'BAL',
            'Buffalo Bills': 'BUF',
            'Carolina Panthers': 'CAR',
            'Chicago Bears': 'CHI',
            'Cincinnati Bengals': 'CIN',
            'Cleveland Browns': 'CLE',
            'Dallas Cowboys': 'DAL',
            'Denver Broncos': 'DEN',
            'Detroit Lions': 'DET',
            'Green Bay Packers': 'GB',
            'Houston Texans': 'HOU',
            'Indianapolis Colts': 'IND',
            'Jacksonville Jaguars': 'JAX',
            'Kansas City Chiefs': 'KC',
            'Las Vegas Raiders': 'LV',
            'Los Angeles Chargers': 'LAC',
            'Los Angeles Rams': 'LAR',
            'Miami Dolphins': 'MIA',
            'Minnesota Vikings': 'MIN',
            'New England Patriots': 'NE',
            'New Orleans Saints': 'NO',
            'New York Giants': 'NYG',
            'New York Jets': 'NYJ',
            'Philadelphia Eagles': 'PHI',
            'Pittsburgh Steelers': 'PIT',
            'San Francisco 49ers': 'SF',
            'Seattle Seahawks': 'SEA',
            'Tampa Bay Buccaneers': 'TB',
            'Tennessee Titans': 'TEN',
            'Washington Commanders': 'WAS'
        }
    
    def get_standings(self, season: Optional[str] = None,
                     conference: Optional[str] = None) -> pd.DataFrame:
        """
        Get NFL standings
        
        Args:
            season: Season year (e.g., '2024')
            conference: 'AFC' or 'NFC'
            
        Returns:
            DataFrame with standings
        """
        try:
            # Use ESPN for standings
            url = self.sources['espn_nfl']
            
            logger.info(f"Fetching NFL standings from {url}")
            
            # Scrape the page
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                standings = tables
                
                # Add metadata
                standings['Conference'] = conference or 'NFL'
                standings['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                standings['Season'] = season or str(datetime.now().year)
                
                return standings
            
            # Try Pro Football Reference as fallback
            return self._get_pfr_standings(season)
            
        except Exception as e:
            logger.error(f"Error getting NFL standings: {str(e)}")
            return pd.DataFrame()
    
    def _get_pfr_standings(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get standings from Pro Football Reference"""
        try:
            year = season or str(datetime.now().year)
            url = f"{self.sources['pro_football_reference']}/years/{year}/"
            
            tables = self._parse_table(url)
            
            if tables is not None and not tables.empty:
                # Add metadata
                tables['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                tables['Source'] = 'Pro Football Reference'
                
                return tables
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"PFR standings fallback failed: {str(e)}")
            return pd.DataFrame()
    
    def get_scores(self, date: Optional[datetime] = None,
                  team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NFL game scores
        
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
            url = f"https://www.espn.com/nfl/scoreboard/_/date/{date_str}"
            
            logger.info(f"Fetching NFL scores for {date_str}")
            
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
            logger.error(f"Error getting NFL scores: {str(e)}")
            return pd.DataFrame()
    
    def get_player_stats(self, stat_type: str = 'season',
                        player: Optional[str] = None,
                        team: Optional[str] = None,
                        position: Optional[str] = None) -> pd.DataFrame:
        """
        Get NFL player statistics
        
        Args:
            stat_type: 'season', 'career', or 'game'
            player: Player name filter
            team: Team filter
            position: Position filter (QB, RB, WR, etc.)
            
        Returns:
            DataFrame with player stats
        """
        try:
            # Use Pro Football Reference for comprehensive stats
            year = datetime.now().year
            
            # Different URLs for different positions
            if position and position.upper() == 'QB':
                url = f"{self.sources['pro_football_reference']}/years/{year}/passing.htm"
            elif position and position.upper() in ['RB', 'FB']:
                url = f"{self.sources['pro_football_reference']}/years/{year}/rushing.htm"
            elif position and position.upper() in ['WR', 'TE']:
                url = f"{self.sources['pro_football_reference']}/years/{year}/receiving.htm"
            else:
                # Default to passing stats
                url = f"{self.sources['pro_football_reference']}/years/{year}/passing.htm"
            
            logger.info(f"Fetching NFL player {stat_type} stats")
            
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
                stats_df['Position_Group'] = position or 'All'
                stats_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return stats_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting player stats: {str(e)}")
            return pd.DataFrame()
    
    def get_team_stats(self, stat_type: str = 'season',
                      team: Optional[str] = None) -> pd.DataFrame:
        """
        Get NFL team statistics
        
        Args:
            stat_type: 'season' or 'game'
            team: Team filter
            
        Returns:
            DataFrame with team stats
        """
        try:
            # Use ESPN for team stats
            url = self.sources['espn_nfl']
            
            logger.info(f"Fetching NFL team {stat_type} stats")
            
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
                    week: Optional[int] = None) -> pd.DataFrame:
        """Get NFL schedule"""
        try:
            if team:
                team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
                url = f"https://www.espn.com/nfl/team/schedule/_/name/{team_abbrev}"
            else:
                url = "https://www.espn.com/nfl/schedule"
            
            logger.info(f"Fetching NFL schedule")
            
            schedule_df = self._parse_table(url)
            
            if schedule_df is not None and not schedule_df.empty:
                # Add metadata
                schedule_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                # Filter by week if specified
                if week and 'Week' in schedule_df.columns:
                    schedule_df = schedule_df[schedule_df['Week'] == str(week)]
                
                return schedule_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting schedule: {str(e)}")
            return pd.DataFrame()
    
    def get_roster(self, team: Optional[str] = None) -> pd.DataFrame:
        """Get NFL team roster"""
        try:
            if not team:
                logger.warning("Team name required for roster lookup")
                return pd.DataFrame()
                
            team_abbrev = self.team_abbrevs.get(team, team.upper()).lower()
            url = f"https://www.espn.com/nfl/team/roster/_/name/{team_abbrev}"
            
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
        """Get NFL injury report"""
        try:
            url = "https://www.espn.com/nfl/injuries"
            
            logger.info("Fetching NFL injury report")
            
            injuries_df = self._parse_table(url)
            
            if injuries_df is not None and not injuries_df.empty:
                injuries_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                return injuries_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting injury report: {str(e)}")
            return pd.DataFrame()
    
    def get_playoffs(self, season: Optional[str] = None) -> pd.DataFrame:
        """Get NFL playoff bracket"""
        try:
            if not season:
                # NFL season runs from September to February
                current_year = datetime.now().year
                if datetime.now().month <= 2:
                    season = str(current_year - 1)
                else:
                    season = str(current_year)
            
            url = f"{self.sources['pro_football_reference']}/years/{season}/playoffs.htm"
            
            logger.info(f"Fetching NFL playoff data for {season}")
            
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
        Get NFL draft picks (NFL-specific method)
        
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
            
            url = f"{self.sources['pro_football_reference']}/years/{year}/draft.htm"
            
            logger.info(f"Fetching NFL draft picks for {year}")
            
            draft_df = self._parse_table(url)
            
            if draft_df is not None and not draft_df.empty:
                # Filter by team if specified
                if team and 'Tm' in draft_df.columns:
                    team_abbrev = self.team_abbrevs.get(team, team.upper())
                    draft_df = draft_df[draft_df['Tm'] == team_abbrev]
                
                # Filter by round if specified
                if round and 'Rnd' in draft_df.columns:
                    draft_df = draft_df[draft_df['Rnd'] == str(round)]
                
                # Add metadata
                draft_df['Draft_Year'] = year
                draft_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d')
                
                return draft_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error getting draft picks: {str(e)}")
            return pd.DataFrame()