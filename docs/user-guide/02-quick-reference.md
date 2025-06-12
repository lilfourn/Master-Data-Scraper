# Master Data Scraper - Quick Reference Card

## Basic Commands

```bash
# Interactive mode (recommended)
python3 main.py

# Quick scrape
python3 main.py scrape URL --element ELEMENT --format FORMAT

# Web crawling
python3 main.py crawl URL --keywords "word1,word2" --element ELEMENT

# View history
python3 main.py history [DOMAIN]

# Clear cache
python3 main.py clear-cache
```

## Element Types

| Element | Description | Example |
|---------|-------------|---------|
| `table` | HTML tables | Data tables, stats |
| `p` | Paragraphs | Article content |
| `h1`-`h6` | Headings | Titles, sections |
| `li` | List items | Bullet points |
| `a` | Links | Navigation, URLs |
| `"custom"` | CSS selector | `"div.content"` |

## Output Formats

| Format | Best For | Extension |
|--------|----------|-----------|
| `csv` | Tables, structured data | .csv |
| `json` | APIs, nested data | .json |
| `txt` | Plain text, articles | .txt |
| `md` | Formatted text, docs | .md |

## Common Options

```bash
--preview        # Preview data before saving
--no-save        # Don't save (dry run)
--format FORMAT  # Output format (csv, json, txt, md)
--element ELEMENT # HTML element to scrape
--debug          # Show detailed output
```

## Crawling Options

```bash
--keywords "word1,word2"  # Search for keywords
--depth N                 # Max crawl depth (default: 3)
--max-pages N            # Max pages to crawl (default: 50)
--follow-external        # Follow external links
```

## Sports Scrapers

```bash
# NBA
python3 Sports/NBA/main.py [standings|scores|stats]

# NFL  
python3 Sports/NFL/main.py [standings|scores|injuries]

# NHL
python3 Sports/NHL/main.py [standings|scores|playoffs]

# WNBA
python3 Sports/WNBA/main.py [standings|scores|stats]
```

## Examples

```bash
# Wikipedia table
python3 main.py scrape https://en.wikipedia.org/wiki/List --element table

# News article
python3 main.py scrape https://news.com/article --element p --format txt

# Documentation crawl
python3 main.py crawl https://docs.python.org --keywords "function" --element p

# Custom selector
python3 main.py scrape https://site.com --element "div.data" --format json
```

## File Organization

```
Data/
├── domain.com/           # One folder per domain
│   ├── 2025-06-11_table.csv
│   ├── crawl_0_2025-06-11_p.txt
│   └── metadata.json
└── _logs/               # Log files
    └── scraper.log
```

## Keyboard Shortcuts

- `Ctrl+C` - Cancel current operation
- `↑↓` - Navigate menus (interactive mode)
- `Enter` - Select option
- `Tab` - Autocomplete

## Configuration

Edit `config/settings.yaml`:
```yaml
timeout: 30              # Request timeout
rate_limit_default: 1.0  # Seconds between requests
cache_ttl: 3600         # Cache duration
data_dir: "Data"        # Output directory
```

## Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| No elements found | Try `--preview` to see available elements |
| 403 Forbidden | Check robots.txt, increase rate limit |
| SSL Error | Set `verify_ssl: false` in config (not recommended) |
| Timeout | Increase timeout in config |
| Encoding | Scraper auto-detects, check output file |

## Need Help?

```bash
python3 main.py --help           # General help
python3 main.py COMMAND --help   # Command help
python3 main.py --debug          # Debug mode
```

---
Version 1.0.0 | [Full Docs](../README.md) | [Examples](EXAMPLES.md) | [Troubleshooting](TROUBLESHOOTING.md)