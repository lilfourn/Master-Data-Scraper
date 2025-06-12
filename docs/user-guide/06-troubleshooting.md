# Troubleshooting Guide

Solutions for common issues with Master Data Scraper.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Scraping Errors](#scraping-errors)
- [Network Issues](#network-issues)
- [Data Issues](#data-issues)
- [Performance Issues](#performance-issues)
- [Sports Scraper Issues](#sports-scraper-issues)

## Installation Issues

### Python Version Error

**Problem**: `Python 3.8+ is required`

**Solution**:
```bash
# Check your Python version
python3 --version

# If needed, install Python 3.8+
# macOS:
brew install python@3.11

# Ubuntu/Debian:
sudo apt update
sudo apt install python3.11

# Windows:
# Download from https://python.org
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'rich'`

**Solution**:
```bash
# Install all dependencies
pip3 install -r requirements.txt

# Or install missing module directly
pip3 install rich beautifulsoup4 requests
```

### Permission Denied

**Problem**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Or install for user only
pip3 install --user -r requirements.txt
```

## Scraping Errors

### No Elements Found

**Problem**: `No table elements found at URL`

**Solution**:
1. Preview available elements:
   ```bash
   python3 main.py scrape https://example.com --element table --preview
   ```

2. Try different element types:
   ```bash
   # Try these in order
   python3 main.py scrape URL --element div --preview
   python3 main.py scrape URL --element p --preview
   python3 main.py scrape URL --element "article" --preview
   ```

3. Use custom selectors:
   ```bash
   # Inspect page and find specific class/id
   python3 main.py scrape URL --element "div.data-table" --format csv
   ```

### JavaScript-Rendered Content

**Problem**: `Empty or missing content from dynamic sites`

**Solution**:
1. Check if content loads via JavaScript:
   ```bash
   # View page source vs rendered content
   curl https://example.com | grep "your-data"
   ```

2. Current workaround - find API endpoints:
   ```bash
   # Check Network tab in browser DevTools
   # Look for JSON/API calls
   python3 main.py scrape https://api.example.com/data --format json
   ```

3. Future solution: JavaScript support planned for v2.0

### Access Denied / 403 Forbidden

**Problem**: `HTTP Error 403: Forbidden`

**Solution**:
1. Check robots.txt:
   ```bash
   curl https://example.com/robots.txt
   ```

2. Respect rate limits:
   ```yaml
   # config/settings.yaml
   rate_limit_default: 2.0  # Increase delay
   ```

3. Rotate user agents:
   ```yaml
   # config/settings.yaml
   user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
   ```

## Network Issues

### SSL Certificate Errors

**Problem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution**:
1. Update certificates:
   ```bash
   # macOS
   brew install ca-certificates
   
   # Or update pip certificates
   pip3 install --upgrade certifi
   ```

2. Temporary workaround (not recommended):
   ```yaml
   # config/settings.yaml
   verify_ssl: false
   ```

### Connection Timeout

**Problem**: `TimeoutError: Request timed out`

**Solution**:
1. Increase timeout:
   ```yaml
   # config/settings.yaml
   timeout: 60  # seconds
   ```

2. Check connectivity:
   ```bash
   # Test connection
   curl -I https://example.com
   ping example.com
   ```

3. Use retry logic:
   ```yaml
   # config/settings.yaml
   max_retries: 5
   ```

### Proxy Issues

**Problem**: `ProxyError: Cannot connect through proxy`

**Solution**:
```bash
# Set proxy environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Or in .env file
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
```

## Data Issues

### Encoding Problems

**Problem**: `UnicodeDecodeError` or garbled text

**Solution**:
1. Force UTF-8 encoding:
   ```python
   # The scraper auto-detects encoding, but you can override
   # in config/settings.yaml
   default_encoding: "utf-8"
   ```

2. Check file after scraping:
   ```bash
   file -I Data/example.com/file.txt
   iconv -f ISO-8859-1 -t UTF-8 file.txt > file_utf8.txt
   ```

### Malformed CSV

**Problem**: `CSV file not opening correctly in Excel`

**Solution**:
1. Use JSON for complex data:
   ```bash
   python3 main.py scrape URL --element table --format json
   ```

2. Check delimiter:
   ```bash
   # View first few lines
   head Data/domain/file.csv
   ```

### Missing Data

**Problem**: `Some columns/rows missing from tables`

**Solution**:
1. Check for multiple tables:
   ```bash
   # Tables are numbered 0, 1, 2...
   # The scraper gets all by default
   ```

2. Use custom selectors for specific table:
   ```bash
   python3 main.py scrape URL --element "table#data-table" --format csv
   ```

## Performance Issues

### Slow Scraping

**Problem**: `Scraping takes too long`

**Solution**:
1. Use async scraping for multiple URLs:
   ```python
   from core import scrape_urls_async
   import asyncio
   
   urls = ["url1", "url2", "url3"]
   results = asyncio.run(scrape_urls_async(urls))
   ```

2. Reduce crawl depth:
   ```bash
   python3 main.py crawl URL --depth 2 --max-pages 20
   ```

3. Enable caching:
   ```yaml
   # config/settings.yaml
   cache_ttl: 7200  # 2 hours
   ```

### Memory Issues

**Problem**: `MemoryError` on large pages

**Solution**:
1. Limit elements extracted:
   ```bash
   # Process in chunks
   python3 main.py scrape URL --element p --limit 100
   ```

2. Clear cache regularly:
   ```bash
   python3 main.py clear-cache
   ```

### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solution**:
```yaml
# config/settings.yaml
rate_limit_default: 3.0  # 3 seconds between requests

# Domain-specific limits
rate_limits:
  api.example.com: 5.0
  sensitive-site.com: 10.0
```

## Sports Scraper Issues

### No Data Returned

**Problem**: `No standings data found`

**Solution**:
1. Check if season is active:
   ```bash
   # Some sports have off-seasons
   python3 Sports/NBA/main.py scores
   ```

2. Try different data source:
   ```bash
   # Each scraper has fallback sources
   python3 Sports/NFL/main.py standings --debug
   ```

### Incorrect Format

**Problem**: `Data not in expected format`

**Solution**:
```bash
# Try different formats
python3 Sports/NHL/main.py standings --format json
python3 Sports/NHL/main.py standings --format csv
```

## Debug Mode

For any issue, enable debug mode for detailed output:

```bash
# General debugging
python3 main.py --debug scrape https://example.com --element table

# Sports scraper debugging  
python3 Sports/NBA/main.py standings --debug
```

## Getting Help

If these solutions don't work:

1. **Check logs**:
   ```bash
   tail -f Data/_logs/scraper.log
   ```

2. **Update to latest version**:
   ```bash
   git pull origin main
   pip3 install -r requirements.txt --upgrade
   ```

3. **Report issue**:
   - Include error message
   - Include debug output
   - Include URL (if not sensitive)
   - File issue at: https://github.com/yourusername/master-data-scraper/issues

## Common Error Messages

| Error | Meaning | Quick Fix |
|-------|---------|-----------|
| `ConnectionError` | Can't reach website | Check internet/URL |
| `TimeoutError` | Site too slow | Increase timeout |
| `403 Forbidden` | Access denied | Check robots.txt |
| `404 Not Found` | Page doesn't exist | Verify URL |
| `ParsingError` | Can't parse HTML | Try different element |
| `RateLimitError` | Too many requests | Increase delay |
| `ValidationError` | Invalid input | Check URL format |

---

**Still stuck?** Run `python3 main.py --debug` and create an issue with the output.