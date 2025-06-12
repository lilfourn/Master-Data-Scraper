# Quick Start Guide

Get up and running with Master Data Scraper in 5 minutes!

## 1. Installation (2 minutes)

```bash
# Clone and enter directory
git clone https://github.com/yourusername/master-data-scraper.git
cd master-data-scraper

# Install dependencies
pip3 install -r requirements.txt
```

## 2. Your First Scrape (30 seconds)

### Interactive Mode (Easiest)

```bash
python3 main.py
```

Follow the prompts:
1. Select "Single Page" 
2. Enter a URL (e.g., `https://example.com`)
3. Choose element type (e.g., `table`)
4. Pick format (e.g., `csv`)
5. Done! Check the `Data/` folder

### Command Line Mode

```bash
# Quick scrape
python3 main.py scrape https://example.com --element table --format csv
```

## 3. Common Use Cases

### Scrape a Table

```bash
# Wikipedia table
python3 main.py scrape https://en.wikipedia.org/wiki/List_of_countries_by_GDP --element table --format csv
```

### Extract Article Text

```bash
# News article
python3 main.py scrape https://example.com/article --element p --format txt
```

### Crawl a Website

```bash
# Find documentation about specific topics
python3 main.py crawl https://docs.python.org/3/ --keywords "function,class" --element p
```

### Sports Data

```bash
# NBA standings
python3 Sports/NBA/main.py standings

# NFL scores
python3 Sports/NFL/main.py scores
```

## 4. Where's My Data?

All scraped data is saved in the `Data/` folder, organized by domain:

```
Data/
├── example.com/
│   ├── 2025-06-11_table.csv
│   └── metadata.json
├── docs.python.org/
│   ├── crawl_0_2025-06-11_p.txt
│   └── crawl_1_2025-06-11_p.txt
└── en.wikipedia.org/
    └── 2025-06-11_table.csv
```

## 5. Tips for Success

### Check What You Can Scrape

Before scraping, preview the available elements:

```bash
python3 main.py scrape https://example.com --element table --preview
```

### Use the Right Format

- **Tables** → CSV
- **Articles** → TXT or MD
- **Structured Data** → JSON
- **Mixed Content** → MD

### Be Ethical

The scraper automatically:
- Respects robots.txt
- Adds delays between requests
- Rotates user agents

### Need Help?

```bash
# View all commands
python3 main.py --help

# Get help for specific command
python3 main.py scrape --help
```

## Next Steps

- Read the full [README](../README.md) for advanced features
- Check [examples](EXAMPLES.md) for more use cases
- Configure settings in `config/settings.yaml`
- Try web crawling with keywords

**Happy Scraping! 🕷️**