"""
Configuration module for Master Data Scraper

This module handles configuration management including settings
loading from YAML files and environment variables.
"""

from .settings import Settings, load_settings, get_settings

__all__ = ['Settings', 'load_settings', 'get_settings']