"""
File organization module for managing scraped data

This module handles domain-based folder organization, file naming,
and metadata management.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Handles file organization and naming for scraped data"""
    
    def __init__(self, base_dir: Path = Path("Data")):
        """
        Initialize the file organizer
        
        Args:
            base_dir: Base directory for all scraped data
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        self.logs_dir = self.base_dir / "_logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def get_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL
        
        Args:
            url: Full URL
            
        Returns:
            Domain name
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing invalid characters
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores and dots
        filename = filename.strip('_.')
        
        return filename
    
    def create_domain_directory(self, url: str, subdomain_path: Optional[str] = None) -> Path:
        """
        Create directory structure for a domain
        
        Args:
            url: URL being scraped
            subdomain_path: Optional subdomain path (e.g., 'nba/scores')
            
        Returns:
            Path to the domain directory
        """
        domain = self.get_domain_from_url(url)
        domain_dir = self.base_dir / domain
        
        if subdomain_path:
            # Create subdirectory structure
            subdomain_path = self.sanitize_filename(subdomain_path)
            domain_dir = domain_dir / subdomain_path
        
        domain_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {domain_dir}")
        
        return domain_dir
    
    def generate_filename(self, 
                         url: str, 
                         element_type: str, 
                         format_type: str,
                         timestamp: Optional[datetime] = None,
                         custom_name: Optional[str] = None) -> Path:
        """
        Generate a filename following the naming convention
        
        Args:
            url: Source URL
            element_type: Type of element scraped (table, h1, etc.)
            format_type: Output format (csv, json, etc.)
            timestamp: Optional timestamp (defaults to now)
            custom_name: Optional custom name component
            
        Returns:
            Full path to the output file
        """
        domain = self.get_domain_from_url(url)
        timestamp = timestamp or datetime.now()
        
        # Format timestamp
        time_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        
        # Build filename components
        components = [time_str]
        
        if custom_name:
            components.append(self.sanitize_filename(custom_name))
        
        components.append(element_type)
        
        # Join components
        filename = "_".join(components) + f".{format_type}"
        
        # Get domain directory
        domain_dir = self.create_domain_directory(url)
        
        return domain_dir / filename
    
    def update_metadata(self, 
                       url: str, 
                       filepath: Path,
                       element_type: str,
                       format_type: str,
                       **kwargs) -> Path:
        """
        Update or create metadata.json for a domain
        
        Args:
            url: Source URL
            filepath: Path to the saved file
            element_type: Type of element scraped
            format_type: Output format
            **kwargs: Additional metadata
            
        Returns:
            Path to metadata file
        """
        domain = self.get_domain_from_url(url)
        domain_dir = self.base_dir / domain
        metadata_file = domain_dir / "metadata.json"
        
        # Load existing metadata or create new
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                'domain': domain,
                'first_scraped': datetime.now().isoformat(),
                'scraping_history': []
            }
        
        # Add new scraping record
        record = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'element_type': element_type,
            'format_type': format_type,
            'file': str(filepath.relative_to(self.base_dir)),
            'file_size': filepath.stat().st_size if filepath.exists() else 0,
            **kwargs
        }
        
        metadata['scraping_history'].append(record)
        metadata['last_scraped'] = record['timestamp']
        metadata['total_scrapes'] = len(metadata['scraping_history'])
        
        # Save updated metadata
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.debug(f"Updated metadata for {domain}")
        return metadata_file
    
    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """
        Get statistics for a specific domain
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary with domain statistics
        """
        domain_dir = self.base_dir / domain
        
        if not domain_dir.exists():
            return {'error': 'Domain not found'}
        
        metadata_file = domain_dir / "metadata.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        
        # Calculate basic stats if no metadata
        files = list(domain_dir.glob('*'))
        return {
            'domain': domain,
            'file_count': len([f for f in files if f.is_file() and f.name != 'metadata.json']),
            'total_size': sum(f.stat().st_size for f in files if f.is_file()),
            'last_modified': max(f.stat().st_mtime for f in files) if files else None
        }
    
    def cleanup_old_files(self, days: int = 30, dry_run: bool = True) -> List[Path]:
        """
        Clean up files older than specified days
        
        Args:
            days: Age threshold in days
            dry_run: If True, only report files that would be deleted
            
        Returns:
            List of deleted (or would-be deleted) files
        """
        from datetime import timedelta
        
        threshold = datetime.now() - timedelta(days=days)
        old_files = []
        
        for file in self.base_dir.rglob('*'):
            if file.is_file() and file.name not in ['metadata.json', '.gitkeep']:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < threshold:
                    old_files.append(file)
                    if not dry_run:
                        file.unlink()
                        logger.info(f"Deleted old file: {file}")
        
        if dry_run:
            logger.info(f"Found {len(old_files)} files older than {days} days")
        else:
            logger.info(f"Deleted {len(old_files)} files older than {days} days")
        
        return old_files
    
    def get_all_domains(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all domains
        
        Returns:
            Dictionary mapping domain names to their statistics
        """
        domains = {}
        
        for domain_dir in self.base_dir.iterdir():
            if domain_dir.is_dir() and not domain_dir.name.startswith(('_', '.')):
                domain = domain_dir.name
                stats = self.get_domain_stats(domain)
                
                # Add file count and last scraped
                files = list(domain_dir.glob('*.csv')) + list(domain_dir.glob('*.json')) + \
                       list(domain_dir.glob('*.md')) + list(domain_dir.glob('*.txt'))
                
                if files:
                    last_file = max(files, key=lambda f: f.stat().st_mtime)
                    last_scraped = datetime.fromtimestamp(last_file.stat().st_mtime)
                    stats['last_scraped'] = last_scraped.strftime('%Y-%m-%d %H:%M:%S')
                    stats['total_files'] = len(files)
                else:
                    stats['last_scraped'] = 'Never'
                    stats['total_files'] = 0
                
                domains[domain] = stats
        
        return domains