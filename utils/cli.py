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
                
                # Get scraping mode (single page or crawl)
                mode = self.get_scrape_mode()
                
                if mode == "single":
                    # Single page scraping flow
                    url = self.get_url_input()
                    
                    # Get data types to scrape
                    data_types = self.get_data_type_selection()
                    
                    # If specific elements selected, get element type
                    if 'elements' in data_types:
                        element_type = self.get_element_selection()
                    else:
                        element_type = None
                    
                    # Configure scraping options based on data types
                    self._configure_from_data_types(data_types)
                    
                    # Ask about customization options
                    customize = Confirm.ask("\nWould you like to further customize scraping options?", default=False)
                    if customize:
                        self._configure_scraping_options()
                    
                    # Perform scraping based on data types
                    if 'elements' in data_types and element_type:
                        # Ask if user wants preview
                        if Confirm.ask("\nWould you like to preview the data before saving?", default=True):
                            self._preview_data(url, element_type)
                        
                        # Get export format
                        export_format = self.get_format_selection()
                        
                        # Ask about filename customization
                        custom_naming = Confirm.ask("\nWould you like to customize the filename?", default=False)
                        if custom_naming:
                            self._configure_naming_options()
                        
                        # Perform scraping
                        self._scrape_and_save(url, element_type, export_format)
                    else:
                        # Multi-type scraping
                        self._scrape_multiple_types(url, data_types)
                    
                elif mode == "crawl":
                    # Web crawling flow
                    url = self.get_url_input()
                    crawl_settings = self.get_crawl_settings()
                    
                    # Get data types to scrape
                    data_types = self.get_data_type_selection()
                    
                    if 'elements' in data_types:
                        element_type = self.get_element_selection()
                        export_format = self.get_format_selection()
                        
                        # Perform crawl and scrape
                        self._crawl_and_scrape(url, element_type, export_format, crawl_settings)
                    else:
                        # Multi-type crawling
                        self._crawl_multiple_types(url, data_types, crawl_settings)
                
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
    
    def _crawl_and_scrape(self, url: str, element_type: str, export_format: str, 
                         crawl_settings: Dict[str, Any]) -> None:
        """Perform web crawling and scraping"""
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        
        # Create progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=self.console
        )
        
        with progress:
            task = progress.add_task("Crawling...", total=crawl_settings['max_pages'])
            
            def update_progress(current, total, message):
                progress.update(task, completed=current, description=message[:50])
            
            try:
                # Perform fast crawl and scrape
                result = self.scraper.fast_crawl_and_scrape(
                    start_url=url,
                    element_type=element_type,
                    keywords=crawl_settings['keywords'],
                    export_format=export_format,
                    max_depth=crawl_settings['max_depth'],
                    max_pages=crawl_settings['max_pages'],
                    max_workers=10,  # Use 10 concurrent workers
                    progress_callback=update_progress
                )
                
                # Show results
                self.show_crawl_results(result['crawl_stats'], result['scraped_pages'])
                
                if result['saved_files']:
                    self.console.print(f"\n[green]✓ Data saved to {len(result['saved_files'])} files[/green]")
                    
            except Exception as e:
                self.console.print(f"\n[red]Crawl failed: {str(e)}[/red]")
                raise
    
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
    
    def get_scrape_mode(self) -> str:
        """Get scraping mode selection from user"""
        choices = [
            questionary.Choice("Single Page  - Scrape one URL only", value="single"),
            questionary.Choice("Crawl Site   - Crawl and scrape multiple pages based on keywords", value="crawl"),
        ]
        
        mode = questionary.select(
            "Select scraping mode:",
            choices=choices
        ).ask()
        
        if mode is None:
            raise KeyboardInterrupt()
        
        return mode
    
    def get_crawl_settings(self) -> Dict[str, Any]:
        """Get crawling settings from user"""
        self.console.print("\n[bold cyan]Configure Web Crawling[/bold cyan]")
        
        # Get keywords
        keywords_input = questionary.text(
            "Enter keywords to search for (comma-separated, or press Enter to crawl all):",
            default=""
        ).ask()
        
        if keywords_input is None:
            raise KeyboardInterrupt()
        
        keywords = [k.strip() for k in keywords_input.split(',') if k.strip()] if keywords_input else []
        
        # Get max depth
        max_depth = questionary.text(
            "Maximum crawl depth (default: 3):",
            default="3",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()
        
        if max_depth is None:
            raise KeyboardInterrupt()
        
        # Get max pages
        max_pages = questionary.text(
            "Maximum pages to crawl (default: 50):",
            default="50",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()
        
        if max_pages is None:
            raise KeyboardInterrupt()
        
        # Follow external links?
        follow_external = questionary.confirm(
            "Follow links to other domains?",
            default=False
        ).ask()
        
        if follow_external is None:
            raise KeyboardInterrupt()
        
        # Fast mode?
        fast_mode = questionary.confirm(
            "Use fast mode (concurrent requests)?",
            default=True
        ).ask()
        
        if fast_mode is None:
            raise KeyboardInterrupt()
        
        return {
            'keywords': keywords,
            'max_depth': int(max_depth),
            'max_pages': int(max_pages),
            'follow_external_links': follow_external,
            'fast_mode': fast_mode
        }
    
    def get_data_type_selection(self) -> List[str]:
        """Get data type selection from user"""
        choices = [
            questionary.Choice("Tables Only  - Extract data from HTML tables", value="tables"),
            questionary.Choice("Text Content - Extract paragraphs and text", value="text"),
            questionary.Choice("Images       - Extract image URLs and metadata", value="images"),
            questionary.Choice("Links        - Extract all hyperlinks", value="links"),
            questionary.Choice("Metadata     - Extract page metadata (title, description, etc.)", value="metadata"),
            questionary.Choice("All Content  - Extract everything", value="all"),
            questionary.Choice("Custom       - Choose specific HTML elements", value="elements"),
        ]
        
        data_type = questionary.select(
            "What type of data would you like to scrape?",
            choices=choices
        ).ask()
        
        if data_type is None:
            raise KeyboardInterrupt()
        
        # Convert selection to list of data types
        if data_type == "all":
            return ["tables", "text", "images", "links", "metadata"]
        elif data_type == "elements":
            return ["elements"]
        else:
            return [data_type]
    
    def _configure_from_data_types(self, data_types: List[str]) -> None:
        """Configure scraping options based on selected data types"""
        if self.settings:
            # Reset all options first
            self.settings.scrape_metadata = False
            self.settings.scrape_scripts = False
            self.settings.scrape_styles = False
            self.settings.scrape_headers = False
            self.settings.scrape_images = False
            
            # Enable based on selection
            if "metadata" in data_types:
                self.settings.scrape_metadata = True
            if "images" in data_types:
                self.settings.scrape_images = True
            if "text" in data_types or "all" in data_types:
                self.settings.scrape_headers = True
    
    def _scrape_multiple_types(self, url: str, data_types: List[str]) -> None:
        """Scrape multiple data types from a single page"""
        results = {}
        
        with self.show_progress("Scraping multiple data types...", None) as progress:
            task = progress.add_task("Scraping...", total=len(data_types))
            
            try:
                for data_type in data_types:
                    progress.update(task, description=f"Scraping {data_type}...")
                    
                    if data_type == "tables":
                        data = self.scraper.scrape(url=url, element_type="table", save=False)
                        if data:
                            results["tables"] = data
                    elif data_type == "text":
                        data = self.scraper.scrape(url=url, element_type="p", save=False)
                        if data:
                            results["text"] = data
                    elif data_type == "images":
                        data = self.scraper.scrape(url=url, element_type="img", save=False)
                        if data:
                            results["images"] = data
                    elif data_type == "links":
                        data = self.scraper.scrape(url=url, element_type="a", save=False)
                        if data:
                            results["links"] = data
                    elif data_type == "metadata":
                        # Scrape metadata using special method
                        self.settings.scrape_metadata = True
                        data = self.scraper.scrape(url=url, element_type="meta", save=False)
                        if data:
                            results["metadata"] = data
                    
                    progress.advance(task)
                
                progress.update(task, completed=True)
                
                # Show results summary
                if results:
                    self.show_multi_type_results(results)
                    
                    # Ask to save
                    if Confirm.ask("\nWould you like to save these results?", default=True):
                        export_format = self.get_format_selection()
                        for data_type, data in results.items():
                            self.scraper.scrape(
                                url=url,
                                element_type=data_type,
                                save=True,
                                export_format=export_format,
                                data=data  # Pass already scraped data
                            )
                        self.console.print("[green]✓ All data saved successfully![/green]")
                else:
                    self.console.print("[yellow]No data found to scrape.[/yellow]")
                    
            except Exception as e:
                progress.update(task, completed=True)
                self.show_error(str(e))
                raise
    
    def _crawl_multiple_types(self, url: str, data_types: List[str], crawl_settings: Dict[str, Any]) -> None:
        """Crawl and scrape multiple data types"""
        self.console.print("[cyan]Multi-type crawling coming soon![/cyan]")
        self.console.print("For now, please use single element type with crawling.")
    
    def show_multi_type_results(self, results: Dict[str, Any]) -> None:
        """Show results from multi-type scraping"""
        self.console.print(f"\n[{Theme.HEADING}]Scraping Results Summary:[/{Theme.HEADING}]")
        
        table = Table(show_header=True, header_style=f"bold {Theme.PRIMARY}", box=box.ROUNDED)
        table.add_column("Data Type", style=Theme.PRIMARY)
        table.add_column("Items Found", style=Theme.SUCCESS)
        
        for data_type, data in results.items():
            count = self._count_elements(data)
            table.add_row(data_type.title(), str(count))
        
        self.console.print(table)
    
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
    
    def show_crawl_results(self, crawl_stats: Dict[str, Any], scraped_pages: int) -> None:
        """Display crawl results summary"""
        # Create summary table
        table = Table(title="Crawl Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Pages Crawled", str(crawl_stats['total_pages']))
        table.add_row("Successful Pages", str(crawl_stats['successful_pages']))
        table.add_row("Failed Pages", str(crawl_stats['failed_pages']))
        table.add_row("Matched Pages", str(crawl_stats['matched_pages']))
        table.add_row("Data Scraped From", str(scraped_pages))
        table.add_row("Duration", f"{crawl_stats['duration']:.1f}s")
        
        self.console.print("\n")
        self.console.print(table)
    
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
    
    def _configure_scraping_options(self) -> None:
        """Configure scraping customization options"""
        self.console.print(f"\n[{Theme.HEADING}]Configure Scraping Options[/{Theme.HEADING}]")
        
        # Update settings based on user choices
        if self.settings:
            self.settings.scrape_metadata = Confirm.ask("Extract page metadata?", default=False)
            self.settings.scrape_scripts = Confirm.ask("Include script elements?", default=False)
            self.settings.scrape_styles = Confirm.ask("Include style elements?", default=False)
            self.settings.scrape_headers = Confirm.ask("Extract header information?", default=True)
            self.settings.scrape_images = Confirm.ask("Extract image information?", default=False)
            self.settings.include_attributes = Confirm.ask("Include element attributes?", default=True)
            self.settings.clean_whitespace = Confirm.ask("Clean whitespace?", default=True)
            
            self.console.print(f"\n[{Theme.SUCCESS}]Scraping options configured![/{Theme.SUCCESS}]")
    
    def _configure_naming_options(self) -> None:
        """Configure file naming options"""
        self.console.print(f"\n[{Theme.HEADING}]Configure File Naming[/{Theme.HEADING}]")
        
        if self.settings:
            # Show available placeholders
            self.console.print(f"\n[{Theme.INFO}]Available placeholders:[/{Theme.INFO}]")
            placeholders = [
                "{timestamp} - Full timestamp",
                "{date} - Date only (YYYYMMDD)",
                "{time} - Time only (HHMMSS)",
                "{domain} - Website domain",
                "{element} - Element type",
                "{title} - Page title",
                "{slug} - URL slug"
            ]
            for p in placeholders:
                self.console.print(f"  [dim]{p}[/dim]")
            
            # Get custom template
            current_template = self.settings.naming_template
            self.console.print(f"\n[dim]Current template: {current_template}[/dim]")
            
            custom_template = Prompt.ask(
                "Enter filename template",
                default=current_template
            )
            if custom_template:
                self.settings.naming_template = custom_template
            
            # Quick options
            self.settings.naming_include_title = Confirm.ask("Include page title?", default=self.settings.naming_include_title)
            self.settings.naming_include_domain = Confirm.ask("Include domain?", default=self.settings.naming_include_domain)
            self.settings.naming_use_url_slug = Confirm.ask("Use URL slug?", default=self.settings.naming_use_url_slug)
            
            self.console.print(f"\n[{Theme.SUCCESS}]Naming options configured![/{Theme.SUCCESS}]")


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