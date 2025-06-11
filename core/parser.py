"""
HTML Parser module for extracting different types of elements

This module provides parsers for various HTML elements including
tables, headings, paragraphs, lists, and links.
"""

from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup, Tag
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class HTMLParser:
    """Factory class for creating appropriate parsers for different HTML elements"""
    
    def __init__(self, html: str, parser: str = "lxml"):
        """
        Initialize the HTML parser
        
        Args:
            html: HTML content to parse
            parser: BeautifulSoup parser to use (default: lxml)
        """
        self.soup = BeautifulSoup(html, parser)
    
    def parse(self, element_type: str, **kwargs) -> Union[List[Dict], pd.DataFrame, List[str]]:
        """
        Parse HTML based on element type
        
        Args:
            element_type: Type of element to parse (table, h1-h6, p, li, a, etc.)
            **kwargs: Additional arguments for specific parsers
            
        Returns:
            Parsed data in appropriate format
        """
        parser_map = {
            'table': self.parse_tables,
            'h1': lambda: self.parse_headings('h1'),
            'h2': lambda: self.parse_headings('h2'),
            'h3': lambda: self.parse_headings('h3'),
            'h4': lambda: self.parse_headings('h4'),
            'h5': lambda: self.parse_headings('h5'),
            'h6': lambda: self.parse_headings('h6'),
            'p': self.parse_paragraphs,
            'li': self.parse_list_items,
            'ul': self.parse_lists,
            'ol': self.parse_lists,
            'a': self.parse_links,
        }
        
        if element_type in parser_map:
            return parser_map[element_type](**kwargs)
        else:
            # Custom CSS selector
            return self.parse_custom(element_type, **kwargs)
    
    def parse_tables(self, index: Optional[int] = None) -> Union[List[pd.DataFrame], pd.DataFrame]:
        """
        Parse HTML tables into pandas DataFrames
        
        Args:
            index: Optional index of specific table to parse
            
        Returns:
            Single DataFrame or list of DataFrames
        """
        tables = self.soup.find_all('table')
        
        if not tables:
            logger.warning("No tables found in HTML")
            return []
        
        dataframes = []
        
        for i, table in enumerate(tables):
            try:
                # Extract table data
                from io import StringIO
                df = pd.read_html(StringIO(str(table)))[0]
                dataframes.append(df)
                logger.debug(f"Parsed table {i} with shape {df.shape}")
            except Exception as e:
                logger.error(f"Error parsing table {i}: {str(e)}")
                continue
        
        if index is not None and 0 <= index < len(dataframes):
            return dataframes[index]
        
        return dataframes
    
    def parse_headings(self, tag: str) -> List[str]:
        """
        Parse heading elements
        
        Args:
            tag: Heading tag (h1-h6)
            
        Returns:
            List of heading texts
        """
        headings = self.soup.find_all(tag)
        return [h.get_text(strip=True) for h in headings]
    
    def parse_paragraphs(self) -> List[str]:
        """
        Parse paragraph elements
        
        Returns:
            List of paragraph texts
        """
        paragraphs = self.soup.find_all('p')
        return [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
    
    def parse_list_items(self) -> List[str]:
        """
        Parse list item elements
        
        Returns:
            List of list item texts
        """
        items = self.soup.find_all('li')
        return [item.get_text(strip=True) for item in items]
    
    def parse_lists(self, list_type: Optional[str] = None) -> List[Dict[str, List[str]]]:
        """
        Parse unordered or ordered lists
        
        Args:
            list_type: 'ul' or 'ol', or None for both
            
        Returns:
            List of dictionaries containing list data
        """
        if list_type:
            lists = self.soup.find_all(list_type)
        else:
            lists = self.soup.find_all(['ul', 'ol'])
        
        result = []
        for lst in lists:
            items = [li.get_text(strip=True) for li in lst.find_all('li')]
            result.append({
                'type': lst.name,
                'items': items
            })
        
        return result
    
    def parse_links(self, absolute_url: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Parse anchor tags
        
        Args:
            absolute_url: Base URL to convert relative links to absolute
            
        Returns:
            List of dictionaries with link data
        """
        from urllib.parse import urljoin
        
        links = self.soup.find_all('a')
        result = []
        
        for link in links:
            href = link.get('href', '')
            if absolute_url and href and not href.startswith(('http://', 'https://')):
                href = urljoin(absolute_url, href)
            
            result.append({
                'text': link.get_text(strip=True),
                'href': href,
                'title': link.get('title', '')
            })
        
        return result
    
    def parse_custom(self, selector: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Parse elements using custom CSS selector
        
        Args:
            selector: CSS selector string
            
        Returns:
            List of dictionaries with element data
        """
        elements = self.soup.select(selector)
        result = []
        
        for elem in elements:
            data = {
                'tag': elem.name,
                'text': elem.get_text(strip=True),
                'attrs': dict(elem.attrs) if elem.attrs else {}
            }
            result.append(data)
        
        return result
    
    def preview_element(self, element_type: str, limit: int = 5) -> str:
        """
        Get a preview of elements to be scraped
        
        Args:
            element_type: Type of element to preview
            limit: Maximum number of elements to show
            
        Returns:
            Preview string
        """
        data = self.parse(element_type)
        
        if isinstance(data, pd.DataFrame):
            return f"DataFrame with shape {data.shape}:\n{data.head(limit)}"
        elif isinstance(data, list) and data:
            preview_items = data[:limit]
            return f"Found {len(data)} items. Preview:\n" + "\n".join(str(item) for item in preview_items)
        else:
            return "No elements found"