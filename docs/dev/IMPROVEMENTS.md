# Performance and Rate Limiting Improvements

## Overview

This document describes the improvements made to handle rate limiting (429 errors) and enhance scraping performance, particularly for sports reference sites like basketball-reference.com.

## Key Improvements

### 1. Enhanced Rate Limiting

- **Domain-specific delays**: Updated `config/domains.yaml` with longer delays for sports reference sites (10 seconds)
- **Smart retry logic**: Exponential backoff for 429 errors with configurable retries
- **Per-domain tracking**: Separate rate limiting for each domain

### 2. Stealth Features

- **User agent rotation**: Added `utils/stealth.py` with realistic browser user agents
- **Browser headers**: Dynamic header generation matching user agent profiles
- **Fingerprint randomization**: Realistic browser fingerprints to avoid detection

### 3. Fast Crawler Implementation

- **Concurrent requests**: `FastCrawler` class with ThreadPoolExecutor for parallel crawling
- **Async option**: `AsyncFastCrawler` for maximum performance on friendly sites
- **Smart filtering**: Skip unnecessary resources (images, videos, ads, tracking URLs)

### 4. Sports Reference Scraper

New specialized scraper for sports reference sites:

```bash
# Use the sports command for basketball-reference.com and similar sites
python main.py sports https://www.basketball-reference.com/wnba/years/2025_per_game.html

# Adjust wait time if needed (default is 10 seconds)
python main.py sports <url> --wait 15

# Scrape specific tables
python main.py sports <url> --tables "per_game,totals"

# Export to different formats
python main.py sports <url> --format xlsx
```

Features:
- Minimum 10-second delay between requests
- Handles tables hidden in HTML comments
- Automatic retry with exponential backoff
- Clean numeric data conversion
- Multiple export formats (CSV, JSON, XLSX)

### 5. HTML Cleaning

The parser now removes:
- Scripts and styles
- Ads and tracking elements
- Social media widgets
- Navigation elements
- Comments and metadata

### 6. Configuration Updates

#### config/domains.yaml
```yaml
rate_limits:
  basketball-reference.com: 10.0  # 10 seconds
  www.basketball-reference.com: 10.0
```

#### config/user_agents.yaml
- Chrome, Firefox, Safari, Edge user agents
- Windows, Mac, Linux variations
- Mobile user agents
- Weighted random selection

## Usage Examples

### Regular Scraping (Fast)
```bash
# Single page
python main.py scrape https://example.com --element table

# Crawl with keywords
python main.py crawl https://example.com --keywords "data,statistics" --max-pages 20
```

### Sports Reference Sites (Careful)
```bash
# Basic usage
python main.py sports https://www.basketball-reference.com/wnba/years/2025_per_game.html

# With longer delay
python main.py sports https://www.basketball-reference.com/leagues/NBA_2024_totals.html --wait 20

# Specific tables only
python main.py sports <url> --tables "advanced,per_game" --format xlsx
```

### Interactive Mode
The interactive CLI automatically detects rate limits and suggests using the sports command.

## Troubleshooting Rate Limits

If you still get 429 errors:

1. **Increase wait time**: Use `--wait 20` or `--wait 30`
2. **Clear cache**: `python main.py clear-cache`
3. **Wait and retry**: Some sites have daily limits
4. **Check robots.txt**: Ensure you're respecting the site's crawling rules

## Performance Tips

1. **For friendly sites**: Use default scraper with fast crawling
2. **For strict sites**: Use sports command with longer delays
3. **Batch operations**: Scrape multiple pages in one session to reuse connections
4. **Use caching**: Responses are cached to avoid repeated requests

## Technical Details

### Request Headers
- Realistic browser user agents
- Accept-Encoding with compression support
- Sec-Fetch headers for modern browsers
- Dynamic referer tracking

### Error Handling
- 429: Exponential backoff with retry
- 403: Suggests checking robots.txt
- Network errors: Automatic retry with backoff
- Parse errors: Graceful degradation

### Concurrency
- Default: 10 concurrent workers
- Configurable: 1-20 workers
- Per-domain rate limiting maintained
- Thread-safe URL tracking