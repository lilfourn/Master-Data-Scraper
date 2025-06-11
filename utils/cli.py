"""
CLI interface module for Master Data Scraper

This module provides the interactive command-line interface using
Rich and questionary for a beautiful terminal experience.
"""

from typing import Optional, List, Dict, Any
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box
from rich.rule import Rule
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from core import WebScraper
    from config import Settings


class InteractiveCLI:
    """Interactive CLI interface for the scraper"""
    
    def __init__(self, console: Console, scraper: Optional['WebScraper'] = None, settings: Optional['Settings'] = None):
        """Initialize the CLI interface"""
        self.console = console
        self.scraper = scraper
        self.settings = settings
        # Import here to avoid circular import
        from core.validator import InputValidator
        self.validator = InputValidator()
    
    def show_welcome_banner(self) -> None:
        """Display welcome banner with ASCII art"""
        banner = """
███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗ 
████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗
██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝
██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗
██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
                                                    
██████╗  █████╗ ████████╗ █████╗                     
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗                    
██║  ██║███████║   ██║   ███████║                    
██║  ██║██╔══██║   ██║   ██╔══██║                    
██████╔╝██║  ██║   ██║   ██║  ██║                    
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝                    
                                                    
███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
        """
        
        self.console.print(banner, style="bold cyan", justify="center")
        self.console.print(Rule(style="cyan"))
        self.console.print(
            "[bold]Professional Web Scraping Made Simple[/bold]\n",
            style="white",
            justify="center"
        )
        
    def run(self) -> None:
        """Main interactive loop"""
        try:
            while True:
                # Clear screen for fresh start
                self.console.clear()
                
                # Show welcome banner
                self.show_welcome_banner()
                
                # Get URL from user
                url = self.get_url_input()
                
                # Get element type
                element_type = self.get_element_selection()
                
                # Ask if user wants preview
                if Confirm.ask("\nWould you like to preview the data before saving?", default=True):
                    self._preview_data(url, element_type)
                
                # Get export format
                export_format = self.get_format_selection()
                
                # Perform scraping
                self._scrape_and_save(url, element_type, export_format)
                
                # Ask to continue
                if not self.ask_continue():
                    self.console.print("\n[yellow]Thank you for using Master Data Scraper![/yellow]")
                    break
                    
        except KeyboardInterrupt:
            self.console.print("\n[red]Operation cancelled by user.[/red]")
        except Exception as e:
            self.show_error(str(e))
            raise
    
    def _preview_data(self, url: str, element_type: str) -> None:
        """Preview data before saving"""
        with self.show_progress("Fetching preview...", None) as progress:
            task = progress.add_task("Fetching preview...", total=None)
            
            try:
                # Scrape without saving
                data = self.scraper.scrape(
                    url=url,
                    element_type=element_type,
                    save=False,
                    preview=True
                )
                
                progress.update(task, completed=True)
                
                if data:
                    self.show_preview(data, element_type)
                else:
                    self.console.print(f"\n[yellow]No {element_type} elements found.[/yellow]")
                    
            except Exception as e:
                progress.update(task, completed=True)
                self.console.print(f"\n[red]Preview failed: {str(e)}[/red]")
    
    def _scrape_and_save(self, url: str, element_type: str, export_format: str) -> None:
        """Perform the actual scraping and saving"""
        with self.show_progress("Scraping data...", None) as progress:
            task = progress.add_task("Scraping data...", total=None)
            
            try:
                # Perform scraping
                data = self.scraper.scrape(
                    url=url,
                    element_type=element_type,
                    save=True,
                    export_format=export_format
                )
                
                progress.update(task, completed=True)
                
                if data:
                    # Get file stats
                    domain = self.validator.extract_domain(url)
                    stats = {
                        'element_count': self._count_elements(data),
                        'format': export_format.upper()
                    }
                    
                    # Show success
                    filepath = self.scraper.file_organizer.generate_filename(
                        url, element_type, export_format
                    )
                    self.show_success(str(filepath), stats)
                else:
                    self.console.print(f"\n[yellow]No {element_type} elements found to save.[/yellow]")
                    
            except Exception as e:
                progress.update(task, completed=True)
                self.show_error(str(e))
                raise
    
    def _count_elements(self, data: Any) -> int:
        """Count number of elements in data"""
        if isinstance(data, list):
            return len(data)
        elif hasattr(data, 'shape'):
            return data.shape[0]
        return 1
    
    def get_url_input(self) -> str:
        """Get URL input from user with validation"""
        from core.validator import InputValidator
        
        while True:
            url = questionary.text(
                "Please enter the full URL you wish to scrape:",
                validate=lambda text: len(text) > 0 or "URL cannot be empty"
            ).ask()
            
            if url is None:  # User cancelled
                raise KeyboardInterrupt()
            
            # Validate URL
            with self.console.status("[bold yellow]Validating URL..."):
                is_valid, result = InputValidator.validate_url(url, check_accessibility=True)
            
            if is_valid:
                self.console.print(Theme.status("URL validated and accessible", "success"), style=Theme.SUCCESS)
                return result
            else:
                self.console.print(Theme.status(result, "error"), style=Theme.ERROR)
                if not Confirm.ask("Would you like to try another URL?"):
                    raise KeyboardInterrupt()
    
    def get_element_selection(self) -> str:
        """Get HTML element type selection from user"""
        choices = [
            questionary.Choice("table     - Extract data from HTML tables", value="table"),
            questionary.Choice("h1-h6     - Extract headings", value="heading"),
            questionary.Choice("p         - Extract paragraphs", value="p"),
            questionary.Choice("li        - Extract list items", value="li"),
            questionary.Choice("a         - Extract links", value="a"),
            questionary.Choice("custom    - Enter custom CSS selector", value="custom"),
        ]
        
        selection = questionary.select(
            "What type of HTML element would you like to extract?",
            choices=choices
        ).ask()
        
        if selection is None:
            raise KeyboardInterrupt()
        
        if selection == "heading":
            # Sub-menu for heading levels
            heading_level = questionary.select(
                "Select heading level:",
                choices=[f"h{i}" for i in range(1, 7)]
            ).ask()
            if heading_level is None:
                raise KeyboardInterrupt()
            return heading_level
        
        elif selection == "custom":
            # Get custom CSS selector
            selector = questionary.text(
                "Enter your CSS selector (e.g., 'div.content', '#main-table'):"
            ).ask()
            if selector is None:
                raise KeyboardInterrupt()
            return selector
        
        return selection
    
    def get_format_selection(self) -> str:
        """Get output format selection from user"""
        choices = [
            questionary.Choice("CSV       - Comma-separated values (best for tables)", value="csv"),
            questionary.Choice("JSON      - JavaScript Object Notation (structured data)", value="json"),
            questionary.Choice("Markdown  - Human-readable formatted text", value="md"),
            questionary.Choice("TXT       - Plain text", value="txt"),
        ]
        
        format_type = questionary.select(
            "Choose your output format:",
            choices=choices
        ).ask()
        
        if format_type is None:
            raise KeyboardInterrupt()
        
        self.console.print(f"Selected: {format_type.upper()}", style=Theme.PRIMARY)
        return format_type
    
    def show_progress(self, task_name: str, total: Optional[int] = None) -> Progress:
        """Create and return a progress bar"""
        if total is not None:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            )
        else:
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            )
        
        return progress
    
    def show_preview(self, data: Any, element_type: str) -> None:
        """Show preview of scraped data"""
        self.console.print(f"\n[{Theme.HEADING}]Preview of scraped data:[/{Theme.HEADING}]")
        
        if hasattr(data, 'head') and hasattr(data, 'shape'):  # DataFrame
            self.console.print(f"\n[{Theme.INFO}]DataFrame with {data.shape[0]} rows and {data.shape[1]} columns[/{Theme.INFO}]")
            # Convert DataFrame to rich Table
            table = Table(show_header=True, header_style=f"bold {Theme.PRIMARY}", box=box.ROUNDED)
            
            # Add columns
            for col in data.columns:
                table.add_column(str(col), style=Theme.MUTED)
            
            # Add preview rows (max 5)
            for idx, row in data.head(5).iterrows():
                table.add_row(*[str(val) for val in row])
            
            self.console.print(table)
            if data.shape[0] > 5:
                self.console.print(f"\n[{Theme.MUTED}]... and {data.shape[0] - 5} more rows[/{Theme.MUTED}]")
        
        elif isinstance(data, list) and data:
            # Show first few items
            preview_count = min(5, len(data))
            table = Table(show_header=True, header_style=f"bold {Theme.PRIMARY}", box=box.ROUNDED)
            
            if isinstance(data[0], dict):
                # Add columns from first item
                for key in data[0].keys():
                    table.add_column(str(key), style=Theme.MUTED)
                
                # Add rows
                for item in data[:preview_count]:
                    table.add_row(*[str(v) for v in item.values()])
            else:
                # Simple list
                table.add_column("Value", style=Theme.MUTED)
                for item in data[:preview_count]:
                    table.add_row(str(item))
            
            self.console.print(table)
            if len(data) > preview_count:
                self.console.print(f"\n[{Theme.MUTED}]... and {len(data) - preview_count} more items[/{Theme.MUTED}]")
        else:
            preview_text = str(data)[:500] + "..." if len(str(data)) > 500 else str(data)
            self.console.print(preview_text, style=Theme.MUTED)
    
    def show_success(self, filepath: str, stats: Dict[str, Any]) -> None:
        """Show success message with file information"""
        panel = Panel(
            f"[green]✓ Data saved successfully![/green]\n\n"
            f"📁 Location: [cyan]{filepath}[/cyan]\n"
            f"📊 Size: [yellow]{stats.get('size', 'Unknown')}[/yellow]\n"
            f"🔗 Elements: [yellow]{stats.get('element_count', 'Unknown')}[/yellow]",
            title="Success",
            border_style="green",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def show_error(self, error_message: str) -> None:
        """Show error message"""
        panel = Panel(
            f"[red]✗ Error occurred:[/red]\n\n{error_message}",
            title="Error",
            border_style="red",
            box=box.ROUNDED
        )
        self.console.print(panel)
    
    def ask_continue(self) -> bool:
        """Ask user if they want to scrape another page"""
        return Confirm.ask("\nWould you like to scrape another page?", default=False)
    
    def get_custom_filename(self) -> Optional[str]:
        """Get optional custom filename from user"""
        if Confirm.ask("Would you like to specify a custom filename?", default=False):
            return questionary.text(
                "Enter custom filename (without extension):",
                validate=lambda text: len(text) > 0 or "Filename cannot be empty"
            ).ask()
        return None


# Rich UI Theme and Components
class Theme:
    """Consistent color scheme for the UI"""
    PRIMARY = "cyan"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    INFO = "blue"
    MUTED = "dim white"
    HEADING = "bold white"
    
    # Status indicators
    SUCCESS_ICON = "[green]✓[/green]"
    ERROR_ICON = "[red]✗[/red]"
    WARNING_ICON = "[yellow]⚠[/yellow]"
    INFO_ICON = "[blue]ℹ[/blue]"
    WORKING_ICON = "[cyan]⚡[/cyan]"
    
    @staticmethod
    def status(message: str, status: str = "info") -> str:
        """Format a status message with icon"""
        icons = {
            "success": Theme.SUCCESS_ICON,
            "error": Theme.ERROR_ICON,
            "warning": Theme.WARNING_ICON,
            "info": Theme.INFO_ICON,
            "working": Theme.WORKING_ICON
        }
        return f"{icons.get(status, '')} {message}"