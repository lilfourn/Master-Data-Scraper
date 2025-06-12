"""
Specialized scraper for Sports Reference family of sites
(basketball-reference.com, baseball-reference.com, etc.)

These sites have strict rate limiting and specific table structures.
"""

import time
import logging
from typing import Any, Dict, Optional, List
from bs4 import BeautifulSoup
import pandas as pd

from .web_scraper import WebScraper
from utils.exceptions import NetworkError

logger = logging.getLogger(__name__)


class SportsReferenceScraper(WebScraper):
    """
    Specialized scraper for Sports Reference sites with enhanced handling
    """
    
    def __init__(self, **kwargs):
        """Initialize with sports-reference specific settings"""
        # Force stealth mode and longer delays
        kwargs['use_stealth'] = True
        kwargs['max_retries'] = 5  # More retries for these sites
        kwargs['backoff_factor'] = 1.0  # Longer backoff
        
        super().__init__(**kwargs)
        
        # Sports Reference specific settings
        self.min_request_delay = 10.0  # Minimum 10 seconds between requests
        self.last_request_time = 0
        
    def _wait_between_requests(self):
        """Ensure minimum delay between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_delay:
            wait_time = self.min_request_delay - elapsed
            logger.info(f"Waiting {wait_time:.1f}s before next request to respect rate limits")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def fetch(self, url: str, **kwargs) -> Any:
        """Override fetch to add extra delay and headers"""
        # Wait between requests
        self._wait_between_requests()
        
        # Add specific headers that work better with sports-reference
        headers = kwargs.get('headers', {})
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        kwargs['headers'] = headers
        
        # Use parent fetch with our modifications
        return super().fetch(url, **kwargs)
    
    def scrape_tables(self, url: str, table_ids: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Scrape tables from sports reference page
        
        Args:
            url: Page URL
            table_ids: Optional list of specific table IDs to scrape
            
        Returns:
            Dictionary mapping table IDs to DataFrames
        """
        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find all tables
            tables = {}
            
            # Sports Reference hides some tables in comments
            # Extract tables from comments first
            comment_tables = self._extract_tables_from_comments(response.text)
            
            # Find regular tables
            for table in soup.find_all('table'):
                table_id = table.get('id', '')
                if table_id and (not table_ids or table_id in table_ids):
                    try:
                        # Convert to DataFrame
                        df = self._parse_sports_table(table)
                        if df is not None and not df.empty:
                            tables[table_id] = df
                            logger.info(f"Scraped table '{table_id}' with {len(df)} rows")
                    except Exception as e:
                        logger.warning(f"Failed to parse table '{table_id}': {e}")
            
            # Add comment tables
            for table_id, table_html in comment_tables.items():
                if not table_ids or table_id in table_ids:
                    try:
                        table_soup = BeautifulSoup(table_html, 'lxml')
                        table_element = table_soup.find('table')
                        if table_element:
                            df = self._parse_sports_table(table_element)
                            if df is not None and not df.empty:
                                tables[table_id] = df
                                logger.info(f"Scraped hidden table '{table_id}' with {len(df)} rows")
                    except Exception as e:
                        logger.warning(f"Failed to parse hidden table '{table_id}': {e}")
            
            return tables
            
        except Exception as e:
            logger.error(f"Error scraping tables from {url}: {e}")
            raise
    
    def _extract_tables_from_comments(self, html: str) -> Dict[str, str]:
        """Extract tables hidden in HTML comments"""
        import re
        
        tables = {}
        # Find all HTML comments
        comment_pattern = r'<!--(.*?)-->'
        comments = re.findall(comment_pattern, html, re.DOTALL)
        
        for comment in comments:
            # Look for tables in comments
            if '<table' in comment and 'id=' in comment:
                # Extract table ID
                id_match = re.search(r'id=["\']([^"\']+)["\']', comment)
                if id_match:
                    table_id = id_match.group(1)
                    tables[table_id] = comment
        
        return tables
    
    def _parse_sports_table(self, table_element) -> Optional[pd.DataFrame]:
        """Parse a sports reference table with special handling"""
        try:
            # Extract headers
            headers = []
            header_row = table_element.find('thead')
            if header_row:
                # Handle multi-level headers
                all_headers = header_row.find_all('tr')
                if len(all_headers) > 1:
                    # Use the last header row
                    header_row = all_headers[-1]
                else:
                    header_row = all_headers[0] if all_headers else None
                
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Extract rows
            rows = []
            tbody = table_element.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    # Skip separator rows
                    if 'thead' in tr.get('class', []):
                        continue
                    
                    row_data = []
                    for td in tr.find_all(['th', 'td']):
                        # Get text and clean it
                        text = td.get_text(strip=True)
                        # Handle special data attributes
                        if td.has_attr('data-stat'):
                            stat_name = td['data-stat']
                            if stat_name == 'player' and td.find('a'):
                                # Extract player link
                                text = td.find('a').get_text(strip=True)
                        row_data.append(text)
                    
                    if row_data:
                        rows.append(row_data)
            
            # Create DataFrame
            if rows:
                df = pd.DataFrame(rows)
                if headers and len(headers) == len(df.columns):
                    df.columns = headers
                
                # Clean numeric columns
                df = self._clean_numeric_columns(df)
                
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing sports table: {e}")
            return None
    
    def _clean_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert numeric columns"""
        for col in df.columns:
            # Skip obvious text columns
            if col.lower() in ['player', 'team', 'name', 'pos', 'position']:
                continue
            
            # Try to convert to numeric
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except:
                pass
        
        return df
    
    def scrape_with_retry(self, url: str, element_type: str = 'table', 
                         max_attempts: int = 3) -> Any:
        """
        Scrape with additional retry logic for 429 errors
        
        Args:
            url: URL to scrape
            element_type: Type of element to scrape
            max_attempts: Maximum number of attempts
            
        Returns:
            Scraped data
        """
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    # Exponential backoff
                    wait_time = self.min_request_delay * (2 ** attempt)
                    logger.info(f"Retry attempt {attempt + 1}/{max_attempts} after {wait_time}s")
                    time.sleep(wait_time)
                
                # Use specialized table scraping for tables
                if element_type == 'table':
                    tables = self.scrape_tables(url)
                    # Return all tables combined or specific handling
                    return tables
                else:
                    # Use regular scraping for other elements
                    return super().scrape(url, element_type)
                    
            except Exception as e:
                if '429' in str(e) or 'rate limit' in str(e).lower():
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        raise NetworkError(
                            f"Rate limited after {max_attempts} attempts. "
                            f"The site is blocking requests. Try again later or "
                            f"increase delays in config/domains.yaml"
                        )
                else:
                    raise
        
        return None


def create_sports_scraper() -> SportsReferenceScraper:
    """Factory function to create a sports reference scraper"""
    return SportsReferenceScraper()