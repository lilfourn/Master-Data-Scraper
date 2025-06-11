#!/usr/bin/env python3
"""
Master Data Scraper - Main Entry Point

A powerful command-line application for web scraping with an intuitive interface.
"""

import sys
import signal
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler

# Initialize console for rich output
console = Console()

__version__ = "1.0.0"
__author__ = "Luke Fournier"


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration"""
    level = logging.DEBUG if debug else logging.INFO
    
    # Create logs directory
    log_dir = Path("Data/_logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure rich handler for console
    console_handler = RichHandler(
        console=console,
        show_time=False,
        show_path=debug,
        markup=True
    )
    
    # Configure file handler
    file_handler = logging.FileHandler(
        log_dir / "scraper.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    )
    
    # Set up root logger
    logging.basicConfig(
        level=level,
        handlers=[console_handler, file_handler],
        format="%(message)s"
    )
    
    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully"""
    console.print("\n[yellow]Interrupt received. Cleaning up...[/yellow]")
    sys.exit(0)


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="Master Data Scraper")
@click.option('--debug', is_flag=True, help='Enable debug mode')
def cli(ctx: click.Context, debug: bool = False):
    """
    Master Data Scraper - Professional web scraping made simple.
    
    Extract data from websites and save it in multiple formats,
    all organized by domain in the Data/ folder.
    """
    # Store debug flag in context
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    # Set up logging
    setup_logging(debug)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # If no subcommand, run interactive mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(interactive)


@cli.command()
@click.pass_context
def interactive(ctx: click.Context):
    """Run the scraper in interactive mode"""
    debug = ctx.obj.get('debug', False)
    
    try:
        # Display welcome banner
        welcome_text = Text.from_markup(
            "[bold cyan]MASTER DATA SCRAPER[/bold cyan] v" + __version__ + "\n" +
            "[italic]Professional Web Scraping Made Simple[/italic]"
        )
        console.print(Panel(welcome_text, border_style="cyan", padding=1))
        
        console.print("\nWelcome! This tool helps you extract data from websites.")
        console.print("All data will be saved to the Data/ folder, organized by domain.\n")
        
        # Import and run the interactive CLI
        from utils.cli import InteractiveCLI
        from core import WebScraper
        from config import get_settings
        
        # Initialize scraper
        settings = get_settings()
        scraper = WebScraper()
        
        # Create and run interactive CLI
        cli_interface = InteractiveCLI(console, scraper, settings)
        cli_interface.run()
        
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user.[/red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('--element', '-e', default='table', help='HTML element to scrape')
@click.option('--format', '-f', default='csv', help='Export format (csv, json, md, txt)')
@click.option('--output', '-o', help='Custom output filename')
@click.option('--no-save', is_flag=True, help='Display results without saving')
@click.option('--preview', '-p', is_flag=True, help='Preview elements before scraping')
@click.pass_context
def scrape(ctx: click.Context, url: str, element: str, format: str, 
           output: Optional[str], no_save: bool, preview: bool):
    """Scrape a URL directly from command line"""
    debug = ctx.obj.get('debug', False)
    
    try:
        from core import WebScraper
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        # Initialize scraper
        scraper = WebScraper()
        
        # Show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Scraping {url}...", total=None)
            
            # Perform scraping
            data = scraper.scrape(
                url=url,
                element_type=element,
                save=not no_save,
                export_format=format,
                preview=preview
            )
            
            progress.update(task, completed=True)
        
        if data:
            console.print(f"\n[green]✓[/green] Successfully scraped {element} elements from {url}")
            if not no_save:
                console.print(f"[dim]Data saved in {format.upper()} format[/dim]")
        else:
            console.print(f"\n[yellow]![/yellow] No {element} elements found at {url}")
            
    except Exception as e:
        console.print(f"\n[red]✗ Scraping failed: {str(e)}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument('domain', required=False)
@click.pass_context
def history(ctx: click.Context, domain: Optional[str]):
    """View scraping history for a domain"""
    try:
        from core import FileOrganizer
        from rich.table import Table
        from datetime import datetime
        
        organizer = FileOrganizer()
        
        if domain:
            # Show specific domain history
            stats = organizer.get_domain_stats(domain)
            if not stats:
                console.print(f"[yellow]No history found for domain: {domain}[/yellow]")
                return
                
            console.print(f"\n[bold]Scraping History for {domain}[/bold]\n")
            console.print(f"Total files: {stats.get('total_files', 0)}")
            console.print(f"Last scraped: {stats.get('last_scraped', 'Never')}")
            
            # Show recent files
            if 'recent_files' in stats:
                table = Table(title="Recent Files")
                table.add_column("File", style="cyan")
                table.add_column("Type", style="green")
                table.add_column("Format", style="yellow")
                table.add_column("Date", style="blue")
                
                for file in stats['recent_files'][:10]:
                    table.add_row(
                        file['filename'],
                        file.get('element_type', 'unknown'),
                        file.get('format', 'unknown'),
                        file.get('date', 'unknown')
                    )
                
                console.print(table)
        else:
            # Show all domains
            all_stats = organizer.get_all_domains()
            if not all_stats:
                console.print("[yellow]No scraping history found[/yellow]")
                return
                
            table = Table(title="All Scraped Domains")
            table.add_column("Domain", style="cyan")
            table.add_column("Files", style="green")
            table.add_column("Last Scraped", style="blue")
            
            for domain, stats in all_stats.items():
                table.add_row(
                    domain,
                    str(stats.get('total_files', 0)),
                    stats.get('last_scraped', 'Never')
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error viewing history: {str(e)}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()


@cli.command()
@click.pass_context
def config(ctx: click.Context):
    """View or edit configuration"""
    try:
        from config import get_settings
        from rich.syntax import Syntax
        import yaml
        
        settings = get_settings()
        config_path = Path("config/settings.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
            
            # Display configuration
            console.print("\n[bold]Current Configuration[/bold]\n")
            syntax = Syntax(
                yaml.dump(config_data, default_flow_style=False),
                "yaml",
                theme="monokai"
            )
            console.print(syntax)
            console.print(f"\n[dim]Configuration file: {config_path}[/dim]")
        else:
            console.print("[yellow]No configuration file found. Using defaults.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error viewing configuration: {str(e)}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()


@cli.command()
@click.option('--memory', is_flag=True, help='Clear only memory cache')
@click.pass_context
def clear_cache(ctx: click.Context, memory: bool):
    """Clear the response cache"""
    try:
        from core import WebScraper
        
        scraper = WebScraper()
        count = scraper.clear_cache(memory_only=memory)
        
        cache_type = "memory" if memory else "all"
        console.print(f"[green]✓[/green] Cleared {count} {cache_type} cache entries")
        
    except Exception as e:
        console.print(f"[red]Error clearing cache: {str(e)}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()


def main():
    """Main entry point"""
    try:
        cli()
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()