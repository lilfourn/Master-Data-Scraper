# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Master Data Scraper is a fully-implemented Python command-line web scraping application with an intuitive interface. It supports scraping data from websites, organizing it by domain, and exporting in multiple formats. The project also includes specialized sports scrapers and advanced anti-detection features.

## Common Development Commands

```bash
# Run in interactive mode (recommended)
python main.py

# Direct scraping
python main.py scrape https://example.com --element table --format csv
python main.py scrape https://example.com --element p --preview

# Web crawling
python main.py crawl https://example.com --keywords "python,tutorial" --max-pages 20

# Smart crawling (stays focused on related content)
python main.py smart-crawl https://example.com --element p --min-relevance 0.4 --keywords "tutorial"

# Sports reference sites (with strict rate limits)
python main.py sports https://www.basketball-reference.com/leagues/NBA_2024.html --wait 10

# View scraping history
python main.py history
python main.py history example.com

# Clear cache
python main.py clear-cache

# View configuration
python main.py config

# Debug mode
python main.py --debug

# Run tests (if available)
pytest tests/

# Code formatting and linting
black .
pylint core/ utils/
mypy core/ utils/

# Install development dependencies
pip install -e ".[dev]"
```

## High-Level Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Modules (`/core/`)
- **scraper.py**: Base scraper class with session management, rate limiting, and retry logic
- **stealth_scraper.py**: Enhanced scraper with anti-detection features using stealth utilities
- **async_scraper.py**: Asynchronous scraper for concurrent operations
- **sports_reference_scraper.py**: Specialized scraper for sports-reference.com sites (handles their strict rate limits)
- **parser.py**: HTML parsing factory with specialized parsers for tables, text, lists, links
- **crawler.py**: Web crawling functionality with keyword matching
- **fast_crawler.py**: High-performance concurrent crawler
- **smart_crawler.py**: Intelligent crawler using relevance analysis to stay on-topic
- **relevance_analyzer.py**: Content relevance scoring using NLP and domain analysis
- **validator.py**: Input validation for URLs, elements, file paths
- **organizer.py**: File organization by domain with metadata tracking
- **exporter.py**: Export system supporting CSV, JSON, Markdown, TXT formats

### Utilities (`/utils/`)
- **cli.py**: Interactive CLI interface using Rich for beautiful terminal UI
- **rate_limiter.py**: Domain-specific rate limiting with adaptive delays
- **stealth.py**: Anti-detection utilities (user-agent rotation, headers, fingerprinting)
- **human_behavior.py**: Human-like browsing simulation (delays, fatigue patterns)
- **cache.py**: Response caching system
- **robots.py**: robots.txt compliance checking
- **exceptions.py**: Custom exception classes

### Configuration (`/config/`)
- **settings.py**: Configuration management with YAML support
- **domains.yaml**: Domain-specific rate limits (e.g., basketball-reference.com: 10s)
- **user_agents.yaml**: User agent pool for rotation
- **stealth.yaml**: Stealth configuration settings

### Sports Scrapers (`/Domains/Sports/`)
- **base.py**: Abstract base class for all sports scrapers
- **NBA/**, **NFL/**, **NHL/**, **WNBA/**: Sport-specific implementations

## Key Architectural Patterns

1. **Factory Pattern**: Parser classes use factory pattern for creating element-specific parsers
2. **Strategy Pattern**: Different export formats implemented as strategies
3. **Session Management**: Persistent sessions per domain with cookie handling
4. **Async/Sync Duality**: Both synchronous and asynchronous scrapers available
5. **Progressive Enhancement**: Basic scraper → Stealth scraper → Sports scraper
6. **Domain-based Organization**: All scraped data organized by domain in Data/ folder

## Important Implementation Details

1. **Rate Limiting**: Strict rate limits for sports-reference sites (10s delay for basketball-reference.com)
2. **Anti-Detection**: Stealth features include user-agent rotation, realistic headers, human-like delays
3. **Error Handling**: Comprehensive error handling with retry logic and user-friendly messages
4. **Caching**: Response caching to reduce redundant requests
5. **robots.txt**: Compliance checking enabled by default
6. **Data Organization**: Files saved as `Data/domain/YYYY-MM-DD_HH-MM-SS_element-type.format`

## Common Issues & Solutions

1. **429 Rate Limit Errors**: Increase delay in config/domains.yaml or use --wait flag
2. **Sports Sites**: Use `python main.py sports` command with longer delays
3. **Dynamic Content**: JavaScript-rendered content not yet supported (planned for v2.0)
4. **Large Files**: Streaming parsers handle large files efficiently

## Task Management

When completing tasks, mark them as complete in `/docs/dev/TASKS.md`. Most Phase 1-3 tasks are completed, including:
- Core scraping functionality
- All export formats
- Rate limiting and robots.txt compliance
- Sports scrapers
- Stealth features
- Async scraping
- Web crawling