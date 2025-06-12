"""
Core module for Master Data Scraper

This module contains the main scraping logic, parsing, exporting, and organization functionality.
"""

from .scraper import BaseScraper
from .web_scraper import WebScraper
from .parser import HTMLParser
from .exporter import ExporterFactory, CSVExporter, JSONExporter, MarkdownExporter, TextExporter
from .organizer import FileOrganizer
from .validator import InputValidator
from .async_scraper import AsyncWebScraper, scrape_urls_async
from .crawler import WebCrawler, CrawlResult
from .sports_reference_scraper import SportsReferenceScraper, create_sports_scraper

__all__ = [
    'BaseScraper',
    'WebScraper',
    'AsyncWebScraper',
    'HTMLParser',
    'ExporterFactory',
    'CSVExporter',
    'JSONExporter',
    'MarkdownExporter',
    'TextExporter',
    'FileOrganizer',
    'InputValidator',
    'WebCrawler',
    'CrawlResult',
    'scrape_urls_async',
    'SportsReferenceScraper',
    'create_sports_scraper'
]