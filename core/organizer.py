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
                         custom_name: Optional[str] = None,
                         prefix: Optional[str] = None,
                         settings: Optional[Any] = None,
                         page_title: Optional[str] = None) -> Path:
        """
        Generate a filename following the naming convention
        
        Args:
            url: Source URL
            element_type: Type of element scraped (table, h1, etc.)
            format_type: Output format (csv, json, etc.)
            timestamp: Optional timestamp (defaults to now)
            custom_name: Optional custom name component
            prefix: Optional prefix for the filename
            settings: Optional settings object for naming customization
            page_title: Optional page title for naming
            
        Returns:
            Full path to the output file
        """
        domain = self.get_domain_from_url(url)
        timestamp = timestamp or datetime.now()
        
        if settings and hasattr(settings, 'naming_template'):
            # Use custom naming template
            filename = self._generate_from_template(
                template=settings.naming_template,
                url=url,
                domain=domain,
                element_type=element_type,
                timestamp=timestamp,
                settings=settings,
                page_title=page_title,
                custom_name=custom_name
            )
        else:
            # Use legacy naming convention
            time_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
            
            # Build filename components
            components = []
            
            if prefix:
                components.append(self.sanitize_filename(prefix))
            
            components.append(time_str)
            
            if custom_name:
                components.append(self.sanitize_filename(custom_name))
            
            components.append(element_type)
            
            # Join components
            filename = "_".join(components)
        
        # Ensure filename doesn't exceed max length
        if settings and hasattr(settings, 'naming_max_length'):
            max_length = settings.naming_max_length - len(format_type) - 1  # Account for extension
            if len(filename) > max_length:
                filename = filename[:max_length]
        
        # Add extension
        filename = f"{filename}.{format_type}"
        
        # Get domain directory
        domain_dir = self.create_domain_directory(url)
        
        return domain_dir / filename
    
    def _generate_from_template(self, template: str, url: str, domain: str, 
                              element_type: str, timestamp: datetime,
                              settings: Any, page_title: Optional[str] = None,
                              custom_name: Optional[str] = None) -> str:
        """
        Generate filename from template string
        
        Args:
            template: Template string with placeholders
            url: Source URL
            domain: Domain name
            element_type: Type of element
            timestamp: Timestamp
            settings: Settings object
            page_title: Optional page title
            custom_name: Optional custom name
            
        Returns:
            Generated filename
        """
        from urllib.parse import urlparse
        import re
        
        # Create URL slug if needed
        url_slug = ""
        if settings.naming_use_url_slug:
            parsed = urlparse(url)
            path = parsed.path.strip('/')
            if path:
                # Convert path to slug
                url_slug = re.sub(r'[^\w\-]', '_', path)
                url_slug = re.sub(r'_+', '_', url_slug)
                url_slug = url_slug.strip('_')[:30]  # Limit length
        
        # Format timestamp based on settings
        date_format = settings.naming_date_format if hasattr(settings, 'naming_date_format') else "%Y%m%d_%H%M%S"
        timestamp_str = timestamp.strftime(date_format)
        
        # Create replacements dictionary
        replacements = {
            'timestamp': timestamp_str,
            'date': timestamp.strftime('%Y%m%d'),
            'time': timestamp.strftime('%H%M%S'),
            'year': timestamp.strftime('%Y'),
            'month': timestamp.strftime('%m'),
            'day': timestamp.strftime('%d'),
            'hour': timestamp.strftime('%H'),
            'minute': timestamp.strftime('%M'),
            'second': timestamp.strftime('%S'),
            'domain': domain.replace('.', '_'),
            'element': element_type,
            'element_type': element_type,
            'title': self.sanitize_filename(page_title[:50]) if page_title else 'untitled',
            'custom': self.sanitize_filename(custom_name) if custom_name else '',
            'slug': url_slug,
        }
        
        # Apply template replacements
        filename = template
        for key, value in replacements.items():
            filename = filename.replace(f'{{{key}}}', value)
        
        # Clean up any empty placeholders or multiple underscores
        filename = re.sub(r'\{[^}]*\}', '', filename)  # Remove unused placeholders
        filename = re.sub(r'_+', '_', filename)  # Remove multiple underscores
        filename = filename.strip('_')  # Remove leading/trailing underscores
        
        return self.sanitize_filename(filename)
    
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