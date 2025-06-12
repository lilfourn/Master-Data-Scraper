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
        from core.stealth_scraper import StealthWebScraper
        from config import get_settings
        
        # Initialize scraper (use stealth scraper for better anti-detection)
        settings = get_settings()
        scraper = StealthWebScraper()
        
        # Create and run interactive CLI
        cli_interface = InteractiveCLI(console, scraper, settings)
        cli_interface.run()
        
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user.[/red]")
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            console.print(f"\n[yellow]⚠ Rate limit error: {error_msg}[/yellow]")
            console.print("\n[dim]Tip: The site is blocking requests. Try these solutions:[/dim]")
            console.print("[dim]1. Wait a few seconds and try again[/dim]")
            console.print("[dim]2. Increase the delay for this domain in config/domains.yaml[/dim]")
            console.print("[dim]3. Use a different URL from the same site[/dim]")
        else:
            console.print(f"\n[red]Error: {error_msg}[/red]")
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
@click.option('--no-metadata', is_flag=True, help='Skip extracting page metadata')
@click.option('--include-scripts', is_flag=True, help='Include script elements')
@click.option('--include-styles', is_flag=True, help='Include style elements')
@click.option('--include-images', is_flag=True, help='Include image information')
@click.option('--naming-template', help='Custom filename template (e.g., "{date}_{title}_{element}")')
@click.option('--use-title', is_flag=True, help='Include page title in filename')
@click.option('--use-domain', is_flag=True, help='Include domain in filename')
@click.pass_context
def scrape(ctx: click.Context, url: str, element: str, format: str, 
           output: Optional[str], no_save: bool, preview: bool,
           no_metadata: bool, include_scripts: bool, include_styles: bool,
           include_images: bool, naming_template: Optional[str],
           use_title: bool, use_domain: bool):
    """Scrape a URL directly from command line"""
    debug = ctx.obj.get('debug', False)
    
    try:
        from core import WebScraper
        from core.stealth_scraper import StealthWebScraper
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from config import get_settings
        
        # Load settings and apply CLI overrides
        settings = get_settings()
        
        # Override settings based on CLI options
        if no_metadata:
            settings.scrape_metadata = False
        if include_scripts:
            settings.scrape_scripts = True
        if include_styles:
            settings.scrape_styles = True
        if include_images:
            settings.scrape_images = True
            
        # Update naming settings if provided
        if naming_template:
            settings.naming_template = naming_template
        if use_title:
            settings.naming_include_title = True
        if use_domain:
            settings.naming_include_domain = True
            
        # Initialize scraper with custom settings
        scraper = StealthWebScraper()
        scraper.settings = settings
        
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
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            console.print(f"\n[yellow]⚠ Rate limit error: {error_msg}[/yellow]")
            console.print("\n[dim]Tip: Try again in a few seconds, or increase the delay for this domain in config/domains.yaml[/dim]")
        else:
            console.print(f"\n[red]✗ Scraping failed: {error_msg}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx: click.Context):
    """View and manage scraper configuration"""
    try:
        from config import get_settings, create_default_config
        from rich.table import Table
        from rich.prompt import Prompt, Confirm
        import yaml
        from pathlib import Path
        
        settings = get_settings()
        
        # Show current configuration
        table = Table(title="Current Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")
        
        # Scraping customization settings
        table.add_row("scrape_metadata", str(settings.scrape_metadata), "Extract page metadata")
        table.add_row("scrape_scripts", str(settings.scrape_scripts), "Include script elements")
        table.add_row("scrape_styles", str(settings.scrape_styles), "Include style elements")
        table.add_row("scrape_headers", str(settings.scrape_headers), "Extract header information")
        table.add_row("scrape_images", str(settings.scrape_images), "Extract image information")
        table.add_row("include_attributes", str(settings.include_attributes), "Include element attributes")
        table.add_row("include_page_info", str(settings.include_page_info), "Include page info in metadata")
        
        # File naming settings
        table.add_row("", "", "")  # Empty row for separation
        table.add_row("naming_template", settings.naming_template, "Filename template")
        table.add_row("naming_date_format", settings.naming_date_format, "Date format in filenames")
        table.add_row("naming_max_length", str(settings.naming_max_length), "Maximum filename length")
        table.add_row("naming_use_url_slug", str(settings.naming_use_url_slug), "Use URL slug in filename")
        
        console.print(table)
        
        # Offer to create/update config file
        if Confirm.ask("\nWould you like to create/update the configuration file?"):
            config_path = Path("config/settings.yaml")
            create_default_config(config_path)
            console.print(f"\n[green]✓[/green] Configuration file created at: {config_path}")
            console.print("[dim]You can edit this file to customize settings permanently.[/dim]")
            
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        if ctx.obj.get('debug', False):
            console.print_exception()


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
@click.argument('url')
@click.option('--element', '-e', default='table', help='HTML element to scrape')
@click.option('--keywords', '-k', help='Keywords to search for (comma-separated)')
@click.option('--depth', '-d', default=3, help='Maximum crawl depth')
@click.option('--max-pages', '-m', default=50, help='Maximum pages to crawl')
@click.option('--format', '-f', default='csv', help='Export format (csv, json, md, txt)')
@click.option('--follow-external', is_flag=True, help='Follow links to other domains')
@click.pass_context
def crawl(ctx: click.Context, url: str, element: str, keywords: Optional[str],
          depth: int, max_pages: int, format: str, follow_external: bool):
    """Crawl a website and scrape matching pages"""
    debug = ctx.obj.get('debug', False)
    
    try:
        from core import WebScraper
        from core.stealth_scraper import StealthWebScraper
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        
        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        
        # Initialize scraper (use stealth for crawling)
        scraper = StealthWebScraper()
        
        console.print(f"\n[cyan]Starting web crawl from {url}[/cyan]")
        if keyword_list:
            console.print(f"Keywords: {', '.join(keyword_list)}")
        console.print(f"Max depth: {depth}, Max pages: {max_pages}\n")
        
        # Progress callback
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console
        )
        
        with progress:
            task = progress.add_task("Crawling...", total=max_pages)
            
            def update_progress(current, total, message):
                progress.update(task, completed=current, description=message)
            
            # Perform fast crawl
            result = scraper.fast_crawl_and_scrape(
                start_url=url,
                element_type=element,
                keywords=keyword_list,
                export_format=format,
                max_depth=depth,
                max_pages=max_pages,
                max_workers=10,  # Use concurrent workers for speed
                progress_callback=update_progress
            )
        
        # Display results
        console.print(f"\n[green]✓ Crawl completed![/green]")
        console.print(f"Pages crawled: {result['crawl_stats']['total_pages']}")
        console.print(f"Successful: {result['crawl_stats']['successful_pages']}")
        
        if keyword_list:
            console.print(f"Pages with keywords: {result['crawl_stats']['matched_pages']}")
        
        console.print(f"Data scraped from: {result['scraped_pages']} pages")
        console.print(f"Files saved: {len(result['saved_files'])}")
        
        if result['saved_files']:
            console.print(f"\n[dim]Data saved to Data/ folder[/dim]")
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            console.print(f"\n[yellow]⚠ Rate limit error: {error_msg}[/yellow]")
            console.print("\n[dim]Tip: Try again in a few seconds, or increase the delay for this domain in config/domains.yaml[/dim]")
        else:
            console.print(f"\n[red]✗ Crawl failed: {error_msg}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command('smart-crawl')
@click.argument('url')
@click.option('--element', '-e', default='table', help='HTML element to scrape')
@click.option('--keywords', '-k', help='Keywords to enhance relevance (comma-separated)')
@click.option('--depth', '-d', default=3, help='Maximum crawl depth')
@click.option('--max-pages', '-m', default=30, help='Maximum pages to crawl')
@click.option('--format', '-f', default='csv', help='Export format (csv, json, md, txt)')
@click.option('--min-relevance', '-r', default=0.4, help='Minimum relevance score (0-1)')
@click.option('--similarity', '-s', default=0.3, help='Similarity threshold (0-1)')
@click.option('--follow-external', is_flag=True, help='Follow links to other domains')
@click.pass_context
def smart_crawl(ctx: click.Context, url: str, element: str, keywords: Optional[str],
                depth: int, max_pages: int, format: str, min_relevance: float,
                similarity: float, follow_external: bool):
    """Smart crawl that stays focused on related content using relevance analysis"""
    debug = ctx.obj.get('debug', False)
    
    try:
        from core import WebScraper
        from core.stealth_scraper import StealthWebScraper
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        from rich.table import Table
        
        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else []
        
        # Initialize scraper (use stealth for smart crawling)
        scraper = StealthWebScraper()
        
        console.print(f"\n[cyan]Starting smart crawl from {url}[/cyan]")
        console.print(f"Relevance threshold: {min_relevance}")
        console.print(f"Similarity threshold: {similarity}")
        if keyword_list:
            console.print(f"Keywords: {', '.join(keyword_list)}")
        console.print(f"Max depth: {depth}, Max pages: {max_pages}\n")
        
        # Progress callback
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console
        )
        
        with progress:
            task = progress.add_task("Smart crawling...", total=max_pages)
            
            def update_progress(current, total, message):
                progress.update(task, completed=current, description=message[:50] + "...")
            
            # Perform smart crawl
            result = scraper.smart_crawl_and_scrape(
                start_url=url,
                element_type=element,
                keywords=keyword_list,
                export_format=format,
                max_depth=depth,
                max_pages=max_pages,
                similarity_threshold=similarity,
                min_relevance_score=min_relevance,
                follow_external_links=follow_external,
                progress_callback=update_progress
            )
        
        # Display results
        console.print(f"\n[green]✓ Smart crawl completed![/green]")
        console.print(f"Pages crawled: {result['crawl_stats']['total_pages']}")
        console.print(f"Successful: {result['crawl_stats']['successful_pages']}")
        console.print(f"Data scraped from: {result['scraped_pages']} pages")
        console.print(f"Files saved: {len(result['saved_files'])}")
        
        # Display relevance report
        if 'relevance_report' in result and result['relevance_report']:
            report = result['relevance_report']
            console.print(f"\n[bold]Relevance Analysis:[/bold]")
            console.print(f"Average relevance score: {report['average_score']:.2f}")
            console.print(f"Pages above threshold: {report['above_threshold']}/{report['total_analyzed']}")
            
            # Show top relevant URLs
            if report.get('top_relevant_urls'):
                table = Table(title="\nTop Relevant Pages")
                table.add_column("URL", style="cyan", max_width=60)
                table.add_column("Score", style="green")
                
                for url, score in report['top_relevant_urls'][:5]:
                    short_url = url if len(url) <= 60 else url[:57] + "..."
                    table.add_row(short_url, f"{score:.2f}")
                
                console.print(table)
        
        if result['saved_files']:
            console.print(f"\n[dim]Data saved to Data/ folder with relevance scores in filenames[/dim]")
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            console.print(f"\n[yellow]⚠ Rate limit error: {error_msg}[/yellow]")
            console.print("\n[dim]Tip: Try again in a few seconds, or increase the delay for this domain[/dim]")
        else:
            console.print(f"\n[red]✗ Smart crawl failed: {error_msg}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


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


@cli.command()
@click.pass_context
def stealth_stats(ctx: click.Context):
    """View stealth scraper statistics"""
    try:
        from core.stealth_scraper import StealthWebScraper
        from rich.table import Table
        
        scraper = StealthWebScraper()
        stats = scraper.get_stealth_stats()
        
        console.print("\n[bold]Stealth Scraper Statistics[/bold]\n")
        
        # General stats
        console.print(f"Total Requests: {stats['total_requests']}")
        console.print(f"Domains Visited: {stats['domains_visited']}")
        console.print(f"Stealth Enabled: {'Yes' if stats['stealth_enabled'] else 'No'}")
        console.print(f"Human Behavior: {'Yes' if stats['human_behavior_enabled'] else 'No'}")
        console.print(f"\nCurrent User Agent: [dim]{stats['current_user_agent']}[/dim]")
        
        # Domain request counts
        if stats['domain_requests']:
            table = Table(title="\nRequests by Domain")
            table.add_column("Domain", style="cyan")
            table.add_column("Requests", style="green")
            
            for domain, count in stats['domain_requests'].items():
                table.add_row(domain, str(count))
            
            console.print(table)
        
        # Adaptive delay stats
        if 'average_response_time' in stats:
            console.print(f"\nAverage Response Time: {stats['average_response_time']:.2f}s")
            console.print(f"Current Delay Setting: {stats['current_delay']:.2f}s")
        
    except Exception as e:
        console.print(f"[red]Error viewing stealth stats: {str(e)}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()


@cli.command()
@click.argument('url')
@click.option('--tables', '-t', help='Comma-separated list of table IDs to scrape')
@click.option('--format', '-f', default='csv', help='Export format (csv, json, xlsx)')
@click.option('--wait', '-w', default=10, type=int, help='Seconds to wait between requests')
@click.pass_context
def sports(ctx: click.Context, url: str, tables: Optional[str], format: str, wait: int):
    """Scrape sports reference sites (basketball-reference.com, etc.)"""
    debug = ctx.obj.get('debug', False)
    
    try:
        from core.sports_reference_scraper import create_sports_scraper
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        # Parse table IDs if provided
        table_ids = [t.strip() for t in tables.split(',')] if tables else None
        
        # Create specialized scraper
        console.print(f"\n[cyan]Using specialized sports scraper with {wait}s delay[/cyan]")
        scraper = create_sports_scraper()
        scraper.min_request_delay = wait
        
        # Show progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Scraping sports data from {url}...", total=None)
            
            # Scrape with retry logic
            data = scraper.scrape_with_retry(url, element_type='table', max_attempts=3)
            
            progress.update(task, completed=True)
        
        if data:
            if isinstance(data, dict):
                # Multiple tables
                console.print(f"\n[green]✓[/green] Found {len(data)} tables")
                for table_id, df in data.items():
                    console.print(f"  - {table_id}: {len(df)} rows × {len(df.columns)} columns")
                    
                    # Save each table
                    if format == 'csv':
                        filename = f"{table_id}.csv"
                        df.to_csv(f"Data/{filename}", index=False)
                        console.print(f"    Saved to Data/{filename}")
                    elif format == 'json':
                        filename = f"{table_id}.json"
                        df.to_json(f"Data/{filename}", orient='records', indent=2)
                        console.print(f"    Saved to Data/{filename}")
                    elif format == 'xlsx':
                        filename = f"{table_id}.xlsx"
                        df.to_excel(f"Data/{filename}", index=False)
                        console.print(f"    Saved to Data/{filename}")
            else:
                console.print(f"\n[green]✓[/green] Successfully scraped data")
        else:
            console.print(f"\n[yellow]![/yellow] No tables found at {url}")
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            console.print(f"\n[yellow]⚠ Rate limit error[/yellow]")
            console.print("\n[dim]This site has very strict rate limits. Try:[/dim]")
            console.print(f"[dim]1. Wait a few minutes before trying again[/dim]")
            console.print(f"[dim]2. Use --wait {wait * 2} to double the delay[/dim]")
            console.print(f"[dim]3. Scrape fewer pages at a time[/dim]")
        else:
            console.print(f"\n[red]✗ Scraping failed: {error_msg}[/red]")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option('--all', 'clean_all', is_flag=True, help='Clean all scraped data')
@click.option('--domain', help='Clean data for specific domain')
@click.option('--days', type=int, help='Clean data older than N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
@click.pass_context
def clean(ctx: click.Context, clean_all: bool, domain: Optional[str], days: Optional[int], dry_run: bool):
    """Clean up scraped data files"""
    from clean_data import main as clean_main
    
    # Create a context for the clean command
    clean_ctx = click.Context(clean_main)
    clean_ctx.params = {
        'clean_all': clean_all,
        'domain': domain,
        'days': days,
        'dry_run': dry_run,
        'data_dir': Path('./Data')
    }
    
    # Run the clean command
    clean_main.invoke(clean_ctx)


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