#!/usr/bin/env python3
# pylint: disable=import-error
"""
Data cleanup script for Master Data Scraper

This script helps manage and clean up scraped data files.3
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box
import time

# Initialize console for rich output
console = Console()

def get_directory_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for entry in path.glob('**/*'):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception as e:
        console.print(f"[red]Error calculating size for {path}: {e}[/red]")
    return total

def format_bytes(bytes_size: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def get_domain_stats(data_dir: Path) -> List[Tuple[str, int, int]]:
    """Get statistics for each domain directory."""
    stats = []
    
    if not data_dir.exists():
        return stats
    
    for domain_dir in data_dir.iterdir():
        if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
            file_count = sum(1 for f in domain_dir.glob('**/*') if f.is_file())
            total_size = get_directory_size(domain_dir)
            stats.append((domain_dir.name, file_count, total_size))
    
    # Sort by size descending
    stats.sort(key=lambda x: x[2], reverse=True)
    return stats

def show_data_summary(data_dir: Path) -> None:
    """Display summary of scraped data."""
    console.print("\n[bold cyan]Analyzing scraped data...[/bold cyan]\n")
    
    with console.status("[bold yellow]Calculating sizes..."):
        stats = get_domain_stats(data_dir)
        total_size = sum(s[2] for s in stats)
        total_files = sum(s[1] for s in stats)
    
    if not stats:
        console.print("[yellow]No scraped data found.[/yellow]")
        return
    
    # Create summary table
    table = Table(
        title="Scraped Data Summary",
        box=box.ROUNDED,
        title_style="bold cyan"
    )
    
    table.add_column("Domain", style="cyan")
    table.add_column("Files", justify="right", style="green")
    table.add_column("Size", justify="right", style="yellow")
    table.add_column("% of Total", justify="right", style="blue")
    
    for domain, file_count, size in stats:
        percentage = (size / total_size * 100) if total_size > 0 else 0
        table.add_row(
            domain,
            str(file_count),
            format_bytes(size),
            f"{percentage:.1f}%"
        )
    
    # Add total row
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_files}[/bold]",
        f"[bold]{format_bytes(total_size)}[/bold]",
        "[bold]100.0%[/bold]"
    )
    
    console.print(table)
    console.print(f"\n[dim]Data directory: {data_dir.absolute()}[/dim]")

def clean_domain(data_dir: Path, domain: str, dry_run: bool = False) -> None:
    """Clean data for a specific domain."""
    domain_path = data_dir / domain
    
    if not domain_path.exists():
        console.print(f"[red]Domain '{domain}' not found in data directory.[/red]")
        return
    
    size = get_directory_size(domain_path)
    file_count = sum(1 for f in domain_path.glob('**/*') if f.is_file())
    
    console.print(f"\n[yellow]Domain: {domain}[/yellow]")
    console.print(f"Files: {file_count}")
    console.print(f"Size: {format_bytes(size)}")
    
    if dry_run:
        console.print("\n[cyan]DRY RUN - No files will be deleted[/cyan]")
        return
    
    if Confirm.ask(f"\nDelete all data for {domain}?", default=False):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Deleting {domain}...", total=None)
            
            try:
                shutil.rmtree(domain_path)
                progress.update(task, completed=True)
                console.print(f"[green]✓ Deleted all data for {domain}[/green]")
            except Exception as e:
                progress.update(task, completed=True)
                console.print(f"[red]✗ Error deleting {domain}: {e}[/red]")

def clean_all_data(data_dir: Path, dry_run: bool = False) -> None:
    """Clean all scraped data."""
    stats = get_domain_stats(data_dir)
    
    if not stats:
        console.print("[yellow]No data to clean.[/yellow]")
        return
    
    total_size = sum(s[2] for s in stats)
    total_files = sum(s[1] for s in stats)
    
    console.print(f"\n[bold red]WARNING: This will delete ALL scraped data![/bold red]")
    console.print(f"Total files: {total_files}")
    console.print(f"Total size: {format_bytes(total_size)}")
    
    if dry_run:
        console.print("\n[cyan]DRY RUN - No files will be deleted[/cyan]")
        return
    
    if Confirm.ask("\nAre you absolutely sure?", default=False):
        if Confirm.ask("Type 'DELETE ALL' to confirm", default=False):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task("Deleting data...", total=len(stats))
                
                for domain, _, _ in stats:
                    domain_path = data_dir / domain
                    try:
                        shutil.rmtree(domain_path)
                        progress.advance(task)
                    except Exception as e:
                        console.print(f"[red]Error deleting {domain}: {e}[/red]")
                
                console.print("[green]✓ All data deleted successfully[/green]")
        else:
            console.print("[yellow]Cancelled - no data was deleted[/yellow]")

def clean_old_data(data_dir: Path, days: int, dry_run: bool = False) -> None:
    """Clean data older than specified days."""
    import datetime
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    files_to_delete = []
    total_size = 0
    
    console.print(f"\n[cyan]Finding files older than {days} days...[/cyan]")
    
    with console.status("[bold yellow]Scanning..."):
        for domain_dir in data_dir.iterdir():
            if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
                for file_path in domain_dir.glob('**/*'):
                    if file_path.is_file():
                        if file_path.stat().st_mtime < cutoff_time:
                            files_to_delete.append(file_path)
                            total_size += file_path.stat().st_size
    
    if not files_to_delete:
        console.print(f"[green]No files older than {days} days found.[/green]")
        return
    
    console.print(f"\nFound {len(files_to_delete)} files ({format_bytes(total_size)})")
    
    if dry_run:
        console.print("\n[cyan]DRY RUN - No files will be deleted[/cyan]")
        # Show sample of files
        console.print("\nSample of files to be deleted:")
        for file_path in files_to_delete[:10]:
            console.print(f"  - {file_path.relative_to(data_dir)}")
        if len(files_to_delete) > 10:
            console.print(f"  ... and {len(files_to_delete) - 10} more")
        return
    
    if Confirm.ask(f"\nDelete {len(files_to_delete)} old files?", default=False):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Deleting old files...", total=len(files_to_delete))
            
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    console.print(f"[red]Error deleting {file_path}: {e}[/red]")
                progress.advance(task)
            
            console.print(f"[green]✓ Deleted {deleted_count} old files[/green]")
            
            # Clean up empty directories
            clean_empty_dirs(data_dir)

def clean_empty_dirs(data_dir: Path) -> None:
    """Remove empty directories."""
    empty_dirs = []
    
    for domain_dir in data_dir.iterdir():
        if domain_dir.is_dir() and not domain_dir.name.startswith('_'):
            # Check if directory is empty
            if not any(domain_dir.iterdir()):
                empty_dirs.append(domain_dir)
    
    if empty_dirs:
        console.print(f"\n[yellow]Found {len(empty_dirs)} empty directories[/yellow]")
        for dir_path in empty_dirs:
            try:
                dir_path.rmdir()
                console.print(f"[green]✓ Removed empty directory: {dir_path.name}[/green]")
            except Exception as e:
                console.print(f"[red]Error removing {dir_path}: {e}[/red]")

@click.command()
@click.option('--all', 'clean_all', is_flag=True, help='Clean all scraped data')
@click.option('--domain', help='Clean data for specific domain')
@click.option('--days', type=int, help='Clean data older than N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
@click.option('--data-dir', type=click.Path(path_type=Path), default='./Data', help='Data directory path')
def main(clean_all: bool, domain: Optional[str], days: Optional[int], dry_run: bool, data_dir: Path):
    """Clean up scraped data files."""
    
    # Show banner
    console.print(Panel.fit(
        "[bold cyan]Master Data Scraper - Data Cleanup[/bold cyan]\n"
        "[dim]Manage your scraped data storage[/dim]",
        box=box.ROUNDED
    ))
    
    # Ensure data directory exists
    if not data_dir.exists():
        console.print(f"[red]Data directory not found: {data_dir}[/red]")
        sys.exit(1)
    
    # Show summary first
    show_data_summary(data_dir)
    
    # Perform requested action
    if clean_all:
        clean_all_data(data_dir, dry_run)
    elif domain:
        clean_domain(data_dir, domain, dry_run)
    elif days:
        clean_old_data(data_dir, days, dry_run)
    else:
        # Interactive mode
        console.print("\n[cyan]What would you like to do?[/cyan]")
        console.print("1. Clean specific domain")
        console.print("2. Clean old data")
        console.print("3. Clean all data")
        console.print("4. Exit")
        
        choice = click.prompt("\nEnter choice", type=int)
        
        if choice == 1:
            domain = click.prompt("Enter domain name")
            clean_domain(data_dir, domain, dry_run)
        elif choice == 2:
            days = click.prompt("Delete files older than (days)", type=int, default=30)
            clean_old_data(data_dir, days, dry_run)
        elif choice == 3:
            clean_all_data(data_dir, dry_run)
        else:
            console.print("[yellow]Exiting...[/yellow]")

if __name__ == "__main__":
    main()