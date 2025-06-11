"""
Caching module for Master Data Scraper

This module provides caching functionality to reduce redundant
requests and improve performance.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional, Dict, Union
from datetime import datetime, timedelta
import pickle
import logging

logger = logging.getLogger(__name__)


class Cache:
    """
    Simple file-based cache for storing scraped data
    """
    
    def __init__(self, 
                 cache_dir: Path = Path(".cache"),
                 default_ttl: int = 3600,
                 max_size_mb: float = 100):
        """
        Initialize cache
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds
            max_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        # Create metadata file
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache metadata: {e}")
        
        return {'entries': {}, 'total_size': 0}
    
    def _save_metadata(self) -> None:
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache metadata: {e}")
    
    def _generate_key(self, url: str, params: Optional[Dict] = None) -> str:
        """
        Generate cache key from URL and parameters
        
        Args:
            url: URL to cache
            params: Additional parameters
            
        Returns:
            Cache key
        """
        key_data = {'url': url}
        if params:
            key_data.update(params)
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Get item from cache
        
        Args:
            url: URL to retrieve
            params: Additional parameters
            
        Returns:
            Cached data or None
        """
        key = self._generate_key(url, params)
        
        if key not in self.metadata['entries']:
            return None
        
        entry = self.metadata['entries'][key]
        
        # Check if expired
        if time.time() > entry['expires_at']:
            self.delete(url, params)
            return None
        
        # Load cached data
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            logger.debug(f"Cache hit for {url}")
            return data
            
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            self.delete(url, params)
            return None
    
    def set(self, url: str, data: Any, 
            params: Optional[Dict] = None, 
            ttl: Optional[int] = None) -> bool:
        """
        Store item in cache
        
        Args:
            url: URL to cache
            data: Data to cache
            params: Additional parameters
            ttl: Time-to-live in seconds
            
        Returns:
            Success status
        """
        key = self._generate_key(url, params)
        ttl = ttl or self.default_ttl
        
        # Check cache size
        if self.metadata['total_size'] >= self.max_size_bytes:
            self._evict_oldest()
        
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            # Save data
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            # Update metadata
            file_size = cache_file.stat().st_size
            self.metadata['entries'][key] = {
                'url': url,
                'params': params,
                'created_at': time.time(),
                'expires_at': time.time() + ttl,
                'size': file_size
            }
            self.metadata['total_size'] += file_size
            self._save_metadata()
            
            logger.debug(f"Cached {url} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Error caching data: {e}")
            return False
    
    def delete(self, url: str, params: Optional[Dict] = None) -> bool:
        """
        Delete item from cache
        
        Args:
            url: URL to delete
            params: Additional parameters
            
        Returns:
            Success status
        """
        key = self._generate_key(url, params)
        
        if key not in self.metadata['entries']:
            return False
        
        cache_file = self.cache_dir / f"{key}.pkl"
        
        try:
            # Remove file
            if cache_file.exists():
                cache_file.unlink()
            
            # Update metadata
            entry = self.metadata['entries'].pop(key)
            self.metadata['total_size'] -= entry['size']
            self._save_metadata()
            
            logger.debug(f"Deleted cache entry for {url}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cache entry: {e}")
            return False
    
    def clear(self) -> int:
        """
        Clear all cache entries
        
        Returns:
            Number of entries cleared
        """
        count = 0
        
        for file in self.cache_dir.glob("*.pkl"):
            try:
                file.unlink()
                count += 1
            except Exception as e:
                logger.error(f"Error deleting cache file {file}: {e}")
        
        self.metadata = {'entries': {}, 'total_size': 0}
        self._save_metadata()
        
        logger.info(f"Cleared {count} cache entries")
        return count
    
    def _evict_oldest(self, target_size: Optional[int] = None) -> int:
        """
        Evict oldest entries to free space
        
        Args:
            target_size: Target size in bytes (defaults to 80% of max)
            
        Returns:
            Number of entries evicted
        """
        target_size = target_size or int(self.max_size_bytes * 0.8)
        count = 0
        
        # Sort entries by creation time
        sorted_entries = sorted(
            self.metadata['entries'].items(),
            key=lambda x: x[1]['created_at']
        )
        
        for key, entry in sorted_entries:
            if self.metadata['total_size'] <= target_size:
                break
            
            # Delete entry
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
            
            self.metadata['total_size'] -= entry['size']
            self.metadata['entries'].pop(key)
            count += 1
        
        self._save_metadata()
        logger.info(f"Evicted {count} cache entries")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache statistics
        """
        valid_entries = sum(
            1 for entry in self.metadata['entries'].values()
            if time.time() <= entry['expires_at']
        )
        
        return {
            'total_entries': len(self.metadata['entries']),
            'valid_entries': valid_entries,
            'expired_entries': len(self.metadata['entries']) - valid_entries,
            'total_size_mb': self.metadata['total_size'] / (1024 * 1024),
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'usage_percent': (self.metadata['total_size'] / self.max_size_bytes) * 100
        }


class ResponseCache(Cache):
    """
    Specialized cache for HTTP responses
    """
    
    def cache_response(self, url: str, response: Any, 
                      element_type: str, ttl: Optional[int] = None) -> bool:
        """
        Cache an HTTP response
        
        Args:
            url: Request URL
            response: Response object
            element_type: Type of element being scraped
            ttl: Time-to-live in seconds
            
        Returns:
            Success status
        """
        params = {'element_type': element_type}
        
        # Determine TTL based on content type
        if ttl is None:
            if 'news' in url or 'blog' in url:
                ttl = 1800  # 30 minutes for news
            elif 'api' in url:
                ttl = 300   # 5 minutes for APIs
            else:
                ttl = self.default_ttl
        
        return self.set(url, response, params, ttl)