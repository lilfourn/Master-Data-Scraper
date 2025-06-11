"""
Settings management module for Master Data Scraper

This module handles loading configuration from YAML files and
environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class Settings:
    """Application settings"""
    
    # Scraping settings
    default_delay: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "MasterDataScraper/1.0"
    respect_robots: bool = True
    verify_ssl: bool = True
    
    # Output settings
    data_dir: str = "./Data"
    timestamp_format: str = "%Y-%m-%d_%H-%M-%S"
    create_metadata: bool = True
    max_file_size_mb: float = 100
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_rotation: str = "daily"
    log_retention_days: int = 30
    
    # Cache settings
    enable_cache: bool = True
    cache_dir: str = ".cache"
    cache_ttl: int = 3600
    cache_max_size_mb: float = 100
    
    # Rate limiting
    rate_limit_default: float = 1.0
    rate_limit_concurrent: int = 5
    
    # Export settings
    default_export_format: str = "csv"
    compress_exports: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """Create Settings instance from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create Settings instance from environment variables"""
        env_mapping = {
            'DEBUG': ('log_level', lambda x: 'DEBUG' if x.lower() == 'true' else 'INFO'),
            'LOG_LEVEL': ('log_level', str),
            'DATA_DIR': ('data_dir', str),
            'DEFAULT_TIMEOUT': ('timeout', int),
            'DEFAULT_DELAY': ('default_delay', float),
            'MAX_RETRIES': ('max_retries', int),
            'USER_AGENT': ('user_agent', str),
            'RATE_LIMIT': ('rate_limit_default', float),
            'ENABLE_CACHE': ('enable_cache', lambda x: x.lower() == 'true'),
            'CACHE_EXPIRY': ('cache_ttl', int),
            'DEFAULT_EXPORT_FORMAT': ('default_export_format', str),
            'COMPRESS_EXPORTS': ('compress_exports', lambda x: x.lower() == 'true'),
        }
        
        settings_dict = {}
        
        for env_var, (setting_name, converter) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    settings_dict[setting_name] = converter(value)
                except Exception as e:
                    logger.warning(f"Error converting env var {env_var}: {e}")
        
        return cls(**settings_dict)


def load_settings(config_file: Optional[Path] = None) -> Settings:
    """
    Load settings from YAML file and environment variables
    
    Args:
        config_file: Path to YAML config file
        
    Returns:
        Settings instance
    """
    settings_dict = {}
    
    # Load from YAML if provided
    if config_file and config_file.exists():
        try:
            with open(config_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data:
                    # Flatten nested structure
                    for section, values in yaml_data.items():
                        if isinstance(values, dict):
                            for key, value in values.items():
                                # Convert snake_case keys
                                settings_key = f"{key}"
                                settings_dict[settings_key] = value
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Create base settings
    settings = Settings.from_dict(settings_dict)
    
    # Override with environment variables
    env_settings = Settings.from_env()
    
    # Merge settings (env takes precedence)
    for key, value in env_settings.__dict__.items():
        if value != getattr(Settings, key, None):  # Only override if changed
            setattr(settings, key, value)
    
    return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance
    
    Returns:
        Settings instance
    """
    global _settings
    
    if _settings is None:
        # Look for config file in standard locations
        config_paths = [
            Path("config/settings.yaml"),
            Path("settings.yaml"),
            Path.home() / ".master_scraper" / "settings.yaml"
        ]
        
        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                logger.info(f"Using config file: {config_file}")
                break
        
        _settings = load_settings(config_file)
    
    return _settings


def create_default_config(output_path: Path = Path("config/settings.yaml")) -> None:
    """
    Create a default configuration file
    
    Args:
        output_path: Path to save the config file
    """
    default_config = {
        'scraping': {
            'default_delay': 1.0,
            'timeout': 30,
            'max_retries': 3,
            'user_agent': 'MasterDataScraper/1.0',
            'respect_robots': True,
            'verify_ssl': True
        },
        'output': {
            'data_dir': './Data',
            'timestamp_format': '%Y-%m-%d_%H-%M-%S',
            'create_metadata': True,
            'max_file_size_mb': 100
        },
        'logging': {
            'log_level': 'INFO',
            'log_file': None,
            'log_rotation': 'daily',
            'log_retention_days': 30
        },
        'cache': {
            'enable_cache': True,
            'cache_dir': '.cache',
            'cache_ttl': 3600,
            'cache_max_size_mb': 100
        },
        'rate_limiting': {
            'rate_limit_default': 1.0,
            'rate_limit_concurrent': 5
        },
        'export': {
            'default_export_format': 'csv',
            'compress_exports': False
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Created default config file: {output_path}")