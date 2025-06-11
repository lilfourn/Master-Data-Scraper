#!/usr/bin/env python3
"""
WNBA Domain Scraper CLI

This script provides a command-line interface for scraping WNBA statistics
including standings, scores, player stats, and more.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

import click
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from Domains.Sports.WNBA.scraper import WNBAScraper

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """WNBA Statistics Scraper - Get WNBA data from multiple sources"""
    ctx.ensure_object(dict)
    ctx.obj['scraper'] = WNBAScraper()
    
    # Show banner
    banner = Panel(
        "[bold cyan]WNBA Statistics Scraper[/bold cyan]\n"
        "[dim]Domain: Sports/WNBA[/dim]\n"
        "[dim]Powered by Master Data Scraper[/dim]",
        box=box.ROUNDED,
        expand=False
    )
    console.print(banner)


@cli.command()
@click.option('--conference', '-c', type=click.Choice(['Eastern', 'Western']), 
              help='Filter by conference')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def standings(ctx, conference, format):
    """Get current WNBA standings"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching WNBA standings..."):
        try:
            data = scraper.get_standings(conference=conference)
            
            if not data.empty:
                # Display preview
                console.print(f"\n[green]Found {len(data)} teams[/green]")
                
                # Save data
                filename = scraper._generate_filename('standings', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No standings data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--date', '-d', type=click.DateTime(formats=['%Y-%m-%d']),
              help='Date for scores (YYYY-MM-DD)')
@click.option('--team', '-t', help='Filter by team name')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def scores(ctx, date, team, format):
    """Get WNBA game scores"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching WNBA scores..."):
        try:
            data = scraper.get_scores(date=date, team=team)
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} games[/green]")
                
                # Save data
                filename = scraper._generate_filename('scores', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No scores data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--type', '-t', 'stat_type', 
              type=click.Choice(['season', 'career', 'game']),
              default='season', help='Type of statistics')
@click.option('--player', '-p', help='Filter by player name')
@click.option('--team', '-T', help='Filter by team')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def player_stats(ctx, stat_type, player, team, format):
    """Get WNBA player statistics"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching player statistics..."):
        try:
            data = scraper.get_player_stats(
                stat_type=stat_type,
                player=player,
                team=team
            )
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} players[/green]")
                
                # Show top scorers preview if PTS column exists
                if 'PTS' in data.columns:
                    preview_table = Table(title="Top Scorers", box=box.ROUNDED)
                    preview_cols = ['Player', 'Tm', 'GP', 'PTS', 'REB', 'AST']
                    
                    for col in preview_cols:
                        if col in data.columns:
                            preview_table.add_column(col)
                    
                    # Sort by points
                    try:
                        sorted_data = data.sort_values('PTS', ascending=False)
                        for _, row in sorted_data.head(5).iterrows():
                            row_data = []
                            for col in preview_cols:
                                if col in data.columns:
                                    row_data.append(str(row[col]))
                            preview_table.add_row(*row_data)
                        
                        console.print(preview_table)
                    except:
                        pass
                
                # Save data
                filename = scraper._generate_filename(f'player_{stat_type}_stats', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No player statistics found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--team', '-t', help='Filter by team')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def team_stats(ctx, team, format):
    """Get WNBA team statistics"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching team statistics..."):
        try:
            data = scraper.get_team_stats(team=team)
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} teams[/green]")
                
                # Save data
                filename = scraper._generate_filename('team_stats', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No team statistics found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--year', '-y', type=int, help='Draft year')
@click.option('--team', '-t', help='Filter by team')
@click.option('--round', '-r', type=int, help='Filter by round')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def draft(ctx, year, team, round, format):
    """Get WNBA draft picks"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching draft picks..."):
        try:
            data = scraper.get_draft_picks(year=year, team=team, round=round)
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} draft picks[/green]")
                
                # Save data
                filename = scraper._generate_filename('draft_picks', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No draft data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.argument('team')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def roster(ctx, team, format):
    """Get WNBA team roster"""
    scraper = ctx.obj['scraper']
    
    with console.status(f"[bold yellow]Fetching roster for {team}..."):
        try:
            data = scraper.get_roster(team)
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} players[/green]")
                
                # Save data
                filename = scraper._generate_filename(f'{team}_roster', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No roster data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def injuries(ctx, format):
    """Get WNBA injury report"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching injury report..."):
        try:
            data = scraper.get_injuries()
            
            if not data.empty:
                console.print(f"\n[green]Found {len(data)} injury entries[/green]")
                
                # Save data
                filename = scraper._generate_filename('injuries', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No injury data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--season', '-s', help='Season year')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def playoffs(ctx, season, format):
    """Get WNBA playoff bracket"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching playoff data..."):
        try:
            data = scraper.get_playoffs(season=season)
            
            if not data.empty:
                console.print(f"\n[green]Found playoff data[/green]")
                
                # Save data
                filename = scraper._generate_filename('playoffs', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No playoff data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--year', '-y', type=int, help='All-Star game year')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def allstar(ctx, year, format):
    """Get WNBA All-Star Game data"""
    scraper = ctx.obj['scraper']
    
    with console.status("[bold yellow]Fetching All-Star game data..."):
        try:
            data = scraper.get_all_star_game(year=year)
            
            if not data.empty:
                console.print(f"\n[green]Found All-Star game data[/green]")
                
                # Save data
                filename = scraper._generate_filename('allstar_game', format)
                filepath = scraper._save_data(data, filename, format)
                console.print(f"\n[green] Saved to:[/green] {filepath}")
            else:
                console.print("[yellow]No All-Star game data found[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


@cli.command()
@click.option('--data-types', '-d', multiple=True,
              type=click.Choice(['standings', 'scores', 'player_stats', 'team_stats',
                               'schedule', 'roster', 'injuries', 'playoffs', 'draft', 'allstar']),
              help='Data types to scrape (can specify multiple)')
@click.option('--format', '-f', type=click.Choice(['csv', 'json', 'md']), 
              default='csv', help='Output format')
@click.pass_context
def scrape_all(ctx, data_types, format):
    """Scrape all or specified WNBA data types"""
    scraper = ctx.obj['scraper']
    
    # Default to main data types if none specified
    if not data_types:
        data_types = ['standings', 'player_stats', 'team_stats']
    
    console.print(f"\n[cyan]Scraping {len(data_types)} data types...[/cyan]")
    
    results = scraper.scrape_all(list(data_types), export_format=format)
    
    # Show results summary
    summary_table = Table(title="Scraping Results", box=box.ROUNDED)
    summary_table.add_column("Data Type", style="cyan")
    summary_table.add_column("Status", style="green")
    summary_table.add_column("File Path")
    
    for data_type, filepath in results.items():
        status = " Success" if filepath else " Failed"
        status_style = "green" if filepath else "red"
        summary_table.add_row(
            data_type,
            f"[{status_style}]{status}[/{status_style}]",
            str(filepath) if filepath else "N/A"
        )
    
    console.print(summary_table)


@cli.command()
@click.pass_context
def sources(ctx):
    """List available data sources"""
    scraper = ctx.obj['scraper']
    
    sources_table = Table(title="WNBA Data Sources", box=box.ROUNDED)
    sources_table.add_column("Source", style="cyan")
    sources_table.add_column("URL")
    
    for name, url in scraper.sources.items():
        sources_table.add_row(name, url)
    
    console.print(sources_table)


if __name__ == '__main__':
    cli()