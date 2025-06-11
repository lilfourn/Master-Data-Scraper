"""
Export module for saving scraped data in various formats

This module provides exporters for CSV, JSON, Markdown, and plain text formats.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import json
import csv
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """Abstract base class for all exporters"""
    
    def __init__(self, output_dir: Path = Path("Data")):
        """
        Initialize the exporter
        
        Args:
            output_dir: Base directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    def export(self, data: Any, filepath: Path, **kwargs) -> Path:
        """
        Export data to file
        
        Args:
            data: Data to export
            filepath: Output file path
            **kwargs: Additional export options
            
        Returns:
            Path to the exported file
        """
        pass
    
    def add_metadata(self, data: Any) -> Dict[str, Any]:
        """Add metadata to exported data"""
        return {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'exporter': self.__class__.__name__,
                'version': '1.0.0'
            },
            'data': data
        }


class CSVExporter(BaseExporter):
    """Exporter for CSV format with enhanced features"""
    
    def normalize_headers(self, headers: List[str]) -> List[str]:
        """Normalize column headers for consistency"""
        import re
        normalized = []
        for header in headers:
            # Convert to string and strip
            header = str(header).strip()
            # Replace spaces and special chars with underscores
            header = re.sub(r'[^\w\s-]', '', header)
            header = re.sub(r'[-\s]+', '_', header)
            # Convert to lowercase
            header = header.lower()
            # Remove leading/trailing underscores
            header = header.strip('_')
            # Ensure non-empty
            if not header:
                header = 'column'
            normalized.append(header)
        return normalized
    
    def export(self, data: Union[pd.DataFrame, List[pd.DataFrame], List[Dict], List[List]], 
               filepath: Path, normalize_headers: bool = True, **kwargs) -> Path:
        """
        Export data to CSV file with enhanced features
        
        Args:
            data: DataFrame, list of DataFrames (multi-table), list of dicts, or list of lists
            filepath: Output file path
            normalize_headers: Whether to normalize column headers
            
        Returns:
            Path to the exported file
        """
        filepath = filepath.with_suffix('.csv')
        
        try:
            # Handle multi-table export
            if isinstance(data, list) and data and isinstance(data[0], pd.DataFrame):
                # Multiple DataFrames - export each with a numbered suffix
                exported_files = []
                for i, df in enumerate(data):
                    table_filepath = filepath.with_name(f"{filepath.stem}_table_{i+1}.csv")
                    self._export_single_table(df, table_filepath, normalize_headers, **kwargs)
                    exported_files.append(table_filepath)
                
                # Create an index file
                index_filepath = filepath.with_name(f"{filepath.stem}_index.txt")
                with open(index_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Multiple tables exported on {datetime.now()}\n")
                    f.write(f"Total tables: {len(data)}\n\n")
                    for i, fp in enumerate(exported_files):
                        f.write(f"Table {i+1}: {fp.name}\n")
                
                logger.info(f"Exported {len(data)} CSV tables to {filepath.parent}")
                return filepath  # Return base filepath
            
            else:
                # Single table export
                return self._export_single_table(data, filepath, normalize_headers, **kwargs)
            
        except Exception as e:
            logger.error(f"Error exporting CSV: {str(e)}")
            raise
    
    def _export_single_table(self, data: Any, filepath: Path, 
                           normalize_headers: bool = True, **kwargs) -> Path:
        """Export a single table to CSV"""
        if isinstance(data, pd.DataFrame):
            # Normalize headers if requested
            if normalize_headers:
                data = data.copy()
                data.columns = self.normalize_headers(data.columns.tolist())
            
            # Export with UTF-8 BOM for better Excel compatibility
            data.to_csv(filepath, index=False, encoding='utf-8-sig', **kwargs)
            
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # List of dictionaries
                df = pd.DataFrame(data)
                if normalize_headers:
                    df.columns = self.normalize_headers(df.columns.tolist())
                df.to_csv(filepath, index=False, encoding='utf-8-sig', **kwargs)
            else:
                # List of lists or simple list
                with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    if isinstance(data[0], list):
                        # Assume first row might be headers
                        if normalize_headers and len(data) > 1:
                            headers = self.normalize_headers([str(h) for h in data[0]])
                            writer.writerow(headers)
                            writer.writerows(data[1:])
                        else:
                            writer.writerows(data)
                    else:
                        writer.writerow(['value'])
                        writer.writerows([[item] for item in data])
        else:
            raise ValueError(f"Unsupported data type for CSV export: {type(data)}")
        
        logger.info(f"Exported CSV to {filepath}")
        return filepath


class JSONExporter(BaseExporter):
    """Exporter for JSON format"""
    
    def export(self, data: Any, filepath: Path, 
               include_metadata: bool = True, **kwargs) -> Path:
        """
        Export data to JSON file
        
        Args:
            data: Any JSON-serializable data
            filepath: Output file path
            include_metadata: Whether to include metadata
            
        Returns:
            Path to the exported file
        """
        filepath = filepath.with_suffix('.json')
        
        try:
            # Convert pandas objects to dict
            if isinstance(data, pd.DataFrame):
                data = data.to_dict(orient='records')
            
            # Add metadata if requested
            if include_metadata:
                export_data = self.add_metadata(data)
            else:
                export_data = data
            
            # Write JSON with pretty printing
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, **kwargs)
            
            logger.info(f"Exported JSON to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {str(e)}")
            raise


class MarkdownExporter(BaseExporter):
    """Exporter for Markdown format"""
    
    def export(self, data: Any, filepath: Path, title: Optional[str] = None, **kwargs) -> Path:
        """
        Export data to Markdown file
        
        Args:
            data: Data to export (DataFrame, list, or dict)
            filepath: Output file path
            title: Optional document title
            
        Returns:
            Path to the exported file
        """
        filepath = filepath.with_suffix('.md')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add title if provided
                if title:
                    f.write(f"# {title}\n\n")
                
                # Add metadata
                f.write(f"*Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                
                # Convert data to markdown
                if isinstance(data, pd.DataFrame):
                    f.write(data.to_markdown(index=False))
                elif isinstance(data, list):
                    if data and isinstance(data[0], dict):
                        # List of dicts to table
                        df = pd.DataFrame(data)
                        f.write(df.to_markdown(index=False))
                    else:
                        # Simple list
                        for item in data:
                            f.write(f"- {item}\n")
                elif isinstance(data, dict):
                    # Dictionary to definition list
                    for key, value in data.items():
                        f.write(f"**{key}**: {value}\n\n")
                else:
                    # Fallback to string representation
                    f.write(str(data))
            
            logger.info(f"Exported Markdown to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting Markdown: {str(e)}")
            raise


class TextExporter(BaseExporter):
    """Exporter for plain text format with enhanced text handling"""
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        import re
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def export(self, data: Any, filepath: Path, 
               add_sections: bool = True,
               normalize_whitespace: bool = True,
               **kwargs) -> Path:
        """
        Export data to plain text file with enhanced formatting
        
        Args:
            data: Data to export
            filepath: Output file path
            add_sections: Whether to add section separators
            normalize_whitespace: Whether to normalize whitespace
            
        Returns:
            Path to the exported file
        """
        filepath = filepath.with_suffix('.txt')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Add header
                if add_sections:
                    f.write("="*50 + "\n")
                    f.write(f"Exported Data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("="*50 + "\n\n")
                
                # Handle different data types
                if isinstance(data, pd.DataFrame):
                    # DataFrame to formatted text
                    text = data.to_string(index=False)
                    if normalize_whitespace:
                        text = self.normalize_whitespace(text)
                    f.write(text)
                    
                elif isinstance(data, list):
                    if data and isinstance(data[0], dict):
                        # List of dicts - format as sections
                        for i, item in enumerate(data):
                            if add_sections and i > 0:
                                f.write("\n" + "-"*30 + "\n\n")
                            for key, value in item.items():
                                text = f"{key}: {value}"
                                if normalize_whitespace:
                                    text = self.normalize_whitespace(text)
                                f.write(f"{text}\n")
                    else:
                        # Simple list - one item per line
                        for item in data:
                            text = str(item)
                            if normalize_whitespace:
                                text = self.normalize_whitespace(text)
                            f.write(f"{text}\n")
                            
                elif isinstance(data, dict):
                    # Dictionary - key: value format
                    max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
                    for key, value in data.items():
                        text = f"{str(key).ljust(max_key_len)}: {value}"
                        if normalize_whitespace:
                            text = self.normalize_whitespace(text)
                        f.write(f"{text}\n")
                        
                else:
                    # Fallback to string representation
                    text = str(data)
                    if normalize_whitespace:
                        text = self.normalize_whitespace(text)
                    f.write(text)
                
                # Add footer
                if add_sections:
                    f.write("\n" + "="*50 + "\n")
                    f.write("End of exported data\n")
            
            logger.info(f"Exported text to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting text: {str(e)}")
            raise


class ExporterFactory:
    """Factory class for creating appropriate exporters"""
    
    _exporters = {
        'csv': CSVExporter,
        'json': JSONExporter,
        'md': MarkdownExporter,
        'markdown': MarkdownExporter,
        'txt': TextExporter,
        'text': TextExporter,
    }
    
    @classmethod
    def create_exporter(cls, format_type: str, **kwargs) -> BaseExporter:
        """
        Create an exporter for the specified format
        
        Args:
            format_type: Export format (csv, json, md, txt)
            **kwargs: Additional arguments for exporter initialization
            
        Returns:
            Exporter instance
            
        Raises:
            ValueError: If format type is not supported
        """
        format_type = format_type.lower()
        
        if format_type not in cls._exporters:
            raise ValueError(f"Unsupported export format: {format_type}. "
                           f"Supported formats: {', '.join(cls._exporters.keys())}")
        
        return cls._exporters[format_type](**kwargs)