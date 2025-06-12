# Master Data Scraper - Examples

Real-world examples to help you get the most out of Master Data Scraper.

## Table of Contents
- [Basic Scraping](#basic-scraping)
- [Advanced Scraping](#advanced-scraping)
- [Web Crawling](#web-crawling)
- [Sports Data](#sports-data)
- [Custom Selectors](#custom-selectors)
- [Batch Operations](#batch-operations)

## Basic Scraping

### Example 1: Wikipedia Tables

Scrape population data from Wikipedia:

```bash
python3 main.py scrape https://en.wikipedia.org/wiki/List_of_countries_by_population --element table --format csv
```

**Output**: `Data/en.wikipedia.org/2025-06-11_table.csv`

### Example 2: News Articles

Extract article content:

```bash
python3 main.py scrape https://www.bbc.com/news/technology --element p --format txt
```

**Output**: `Data/www.bbc.com/2025-06-11_p.txt`

### Example 3: Product Listings

Scrape e-commerce data:

```bash
python3 main.py scrape https://example-store.com/products --element "div.product" --format json
```

## Advanced Scraping

### Example 4: Multiple Element Types

Interactive mode for complex pages:

```bash
python3 main.py
```

Then:
1. Choose "Single Page"
2. Enter URL
3. Try different elements (table, h2, li)
4. Preview before saving

### Example 5: Headings Hierarchy

Extract all headings from documentation:

```bash
# Get all h2 headings
python3 main.py scrape https://docs.python.org/3/tutorial/ --element h2 --format md

# Get all h3 headings
python3 main.py scrape https://docs.python.org/3/tutorial/ --element h3 --format md
```

## Web Crawling

### Example 6: Documentation Crawling

Find specific topics in documentation:

```bash
python3 main.py crawl https://docs.python.org/3/ \
  --keywords "decorator,generator,async" \
  --element p \
  --depth 3 \
  --max-pages 30
```

**Output**: Multiple files in `Data/docs.python.org/` with matching content

### Example 7: Blog Crawling

Crawl a blog for specific topics:

```bash
python3 main.py crawl https://example-blog.com \
  --keywords "machine learning,AI,neural network" \
  --element "article" \
  --format md \
  --max-pages 50
```

### Example 8: Site Mapping

Crawl without keywords to map site structure:

```bash
python3 main.py crawl https://small-site.com \
  --element a \
  --depth 2 \
  --max-pages 100
```

## Sports Data

### Example 9: NBA Season Data

```bash
# Current standings
python3 Sports/NBA/main.py standings --format csv

# Recent scores
python3 Sports/NBA/main.py scores --format json

# Player stats
python3 Sports/NBA/main.py stats
```

### Example 10: NFL Week Summary

```bash
# Get all NFL data for the week
python3 Sports/NFL/main.py standings --save
python3 Sports/NFL/main.py scores --save
python3 Sports/NFL/main.py injuries --format csv
```

### Example 11: Multi-Sport Dashboard

```bash
# Collect data from all sports
for sport in NBA NFL NHL WNBA; do
    python3 Sports/$sport/main.py standings --format json
done
```

## Custom Selectors

### Example 12: Complex CSS Selectors

```bash
# Get specific div content
python3 main.py scrape https://example.com \
  --element "div.main-content > p:not(.ad)" \
  --format txt

# Extract code blocks
python3 main.py scrape https://tutorial-site.com \
  --element "pre.language-python" \
  --format txt

# Get navigation links
python3 main.py scrape https://example.com \
  --element "nav ul li a" \
  --format json
```

### Example 13: Data Attributes

```bash
# Select by data attributes
python3 main.py scrape https://modern-site.com \
  --element "[data-testid='product-card']" \
  --format json
```

## Batch Operations

### Example 14: Scraping Multiple Pages

Create a script `batch_scrape.py`:

```python
import subprocess

urls = [
    "https://site1.com/page1",
    "https://site1.com/page2",
    "https://site2.com/data"
]

for url in urls:
    subprocess.run([
        "python3", "main.py", "scrape", url,
        "--element", "table",
        "--format", "csv"
    ])
```

### Example 15: Async Batch Scraping

Using the async API:

```python
import asyncio
from core import scrape_urls_async

async def batch_scrape():
    urls = [
        "https://api1.com/data",
        "https://api2.com/stats",
        "https://api3.com/info"
    ]
    
    results = await scrape_urls_async(urls, "table", max_concurrent=5)
    
    for url, result in results.items():
        if result['success']:
            print(f"✓ {url}: {result['element_count']} elements")
        else:
            print(f"✗ {url}: {result['error']}")

asyncio.run(batch_scrape())
```

## Interactive Mode Examples

### Example 16: Guided Scraping

Best for beginners or exploring new sites:

```
$ python3 main.py

[Interactive session]
1. Select "Single Page"
2. Enter: https://example.com/data
3. Select: "table"
4. Preview: Yes (see data before saving)
5. Format: "csv"
6. Continue: No (exit after one scrape)
```

### Example 17: Crawl Mode

For discovering content:

```
$ python3 main.py

[Interactive session]
1. Select "Crawl Site"
2. Enter: https://docs.example.com
3. Keywords: "api,reference,guide"
4. Max depth: 3
5. Max pages: 25
6. Follow external: No
7. Element: "p"
8. Format: "md"
```

## Tips and Tricks

### Preview First

Always preview when scraping a new site:

```bash
python3 main.py scrape https://new-site.com --element table --preview
```

### Use History

Check what you've scraped before:

```bash
# See all domains
python3 main.py history

# See specific domain
python3 main.py history example.com
```

### Debug Mode

When things don't work as expected:

```bash
python3 main.py --debug scrape https://problem-site.com --element table
```

### Rate Limiting

For sensitive sites, add custom delays:

```yaml
# In config/settings.yaml
rate_limits:
  sensitive-api.com: 5.0  # 5 seconds between requests
```

## Common Patterns

### News Sites
- Element: `article`, `p`, `h1`
- Format: `txt` or `md`

### E-commerce
- Element: `div.product`, `table`
- Format: `json` or `csv`

### Documentation
- Element: `p`, `pre`, `h2`
- Format: `md`
- Use crawling with keywords

### APIs/Data Tables
- Element: `table`
- Format: `csv` or `json`

### Forums/Comments
- Element: `div.post`, `li`
- Format: `json`

---

**Need more examples?** Check the [README](../README.md) or run `python3 main.py --help`