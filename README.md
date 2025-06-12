# Master Data Scraper

A powerful and user-friendly command-line web scraping tool with an intuitive interface, built for both beginners and advanced users.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-brightgreen)

## 🚀 Features

### Core Features
- **🎯 Interactive CLI**: Beautiful guided interface for easy web scraping
- **📊 Multiple Formats**: Export data as CSV, JSON, Markdown, or plain text
- **📁 Smart Organization**: Automatically organizes scraped data by domain
- **🔍 Web Crawling**: Crawl entire websites based on keywords
- **⚡ Async Support**: High-performance concurrent scraping
- **🎨 Rich Terminal UI**: Colorful output with progress bars and status indicators

### Advanced Features
- **🤖 Ethical Scraping**: Built-in rate limiting and robots.txt compliance
- **👤 User-Agent Rotation**: Rotate user agents to avoid detection
- **💾 Response Caching**: Cache responses to reduce redundant requests
- **🏃 Sports Scrapers**: Specialized scrapers for NBA, NFL, NHL, and WNBA data
- **🔐 Authentication Support**: Handle cookies and authentication
- **🛡️ Error Recovery**: Robust error handling with retry logic

### New in v1.0.0
- **🎛️ Scraping Customization**: Toggle what data to extract (metadata, scripts, styles, images)
- **📝 Flexible Naming**: Custom filename templates with placeholders
- **⚙️ Enhanced Configuration**: Comprehensive settings file support
- **🎨 Interactive Options**: Configure scraping behavior on-the-fly

## 📋 Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Interactive Mode](#interactive-mode)
  - [Command Line Mode](#command-line-mode)
  - [Web Crawling](#web-crawling)
  - [Sports Scrapers](#sports-scrapers)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## 🔧 Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/yourusername/master-data-scraper.git
cd master-data-scraper

# Install dependencies
pip install -r requirements.txt
```

### Detailed Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/master-data-scraper.git
cd master-data-scraper

# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

### Verify Installation

```bash
# Check version
python main.py --version

# View help
python main.py --help
```

## 🚀 Quick Start

### Interactive Mode (Recommended for Beginners)

Simply run:
```bash
python main.py
```

The interactive mode will guide you through:
1. Choosing between single page scraping or web crawling
2. Entering the URL to scrape
3. Selecting the HTML elements to extract
4. Choosing the output format
5. Saving your data

### Command Line Mode

For quick, one-line scraping:
```bash
# Scrape tables from a webpage
python main.py scrape https://example.com --element table --format csv

# Scrape with preview
python main.py scrape https://example.com --element p --preview

# Scrape without saving (dry run)
python main.py scrape https://example.com --element h1 --no-save
```

## 📖 Usage

### Interactive Mode

The interactive mode provides a user-friendly interface:

```bash
python main.py
```

You'll be presented with options to:
- **Single Page**: Scrape data from one URL
- **Crawl Site**: Crawl multiple pages based on keywords

### Command Line Mode

#### Basic Scraping

```bash
# Scrape tables and save as CSV
python main.py scrape https://example.com/data --element table --format csv

# Scrape paragraphs and save as text
python main.py scrape https://example.com/article --element p --format txt

# Scrape headings with preview
python main.py scrape https://example.com --element h1 --preview

# Custom CSS selector
python main.py scrape https://example.com --element "div.content" --format json
```

#### Available Elements
- `table` - HTML tables
- `h1` to `h6` - Headings
- `p` - Paragraphs
- `li` - List items
- `a` - Links
- Custom CSS selectors

#### Output Formats
- `csv` - Comma-separated values (best for tables)
- `json` - JavaScript Object Notation (structured data)
- `md` - Markdown (human-readable)
- `txt` - Plain text

### Customization Options

#### Scraping Options

Control what data gets extracted:

```bash
# Skip metadata extraction
python main.py scrape https://example.com --no-metadata

# Include scripts and styles
python main.py scrape https://example.com --include-scripts --include-styles

# Include image information
python main.py scrape https://example.com --include-images
```

#### Custom File Naming

Use templates for organized file naming:

```bash
# Use custom naming template
python main.py scrape https://example.com --naming-template "{date}_{title}_{element}"

# Quick naming options
python main.py scrape https://example.com --use-title --use-domain
```

Available placeholders:
- `{timestamp}`, `{date}`, `{time}` - Time-based naming
- `{domain}`, `{element}`, `{title}` - Content-based naming
- `{year}`, `{month}`, `{day}` - Date components

See [Customization Guide](docs/user-guide/04-customization.md) for detailed options.

### Web Crawling

Crawl websites and extract data from multiple pages:

```bash
# Crawl with keywords
python main.py crawl https://docs.python.org --keywords "function,class" --element p

# Crawl with depth limit
python main.py crawl https://example.com --depth 3 --max-pages 50

# Crawl and follow external links
python main.py crawl https://example.com --follow-external --keywords "tutorial"
```

#### Crawl Options
- `--keywords` - Comma-separated keywords to search for
- `--depth` - Maximum crawl depth (default: 3)
- `--max-pages` - Maximum pages to crawl (default: 50)
- `--follow-external` - Follow links to other domains

### Sports Scrapers

Specialized scrapers for sports data:

```bash
# NBA data
python Sports/NBA/main.py standings
python Sports/NBA/main.py scores
python Sports/NBA/main.py stats --format json

# NFL data
python Sports/NFL/main.py standings --save
python Sports/NFL/main.py scores --format csv

# NHL data
python Sports/NHL/main.py standings
python Sports/NHL/main.py scores

# WNBA data
python Sports/WNBA/main.py standings
python Sports/WNBA/main.py stats
```

### Viewing History

Check your scraping history:

```bash
# View all scraped domains
python main.py history

# View history for specific domain
python main.py history example.com
```

### Cache Management

```bash
# Clear all cache
python main.py clear-cache

# Clear only memory cache
python main.py clear-cache --memory
```

## ⚙️ Configuration

### Configuration File

Create `config/settings.yaml`:

```yaml
# Request settings
timeout: 30
max_retries: 3
user_agent: "Mozilla/5.0 (compatible; MasterDataScraper/1.0)"

# Rate limiting
rate_limit_default: 1.0  # seconds between requests
rate_limits:
  example.com: 2.0
  api.example.com: 0.5

# Cache settings
cache_ttl: 3600  # seconds
cache_dir: ".cache/responses"

# Output settings
data_dir: "Data"
default_format: "csv"

# SSL verification
verify_ssl: true
```

### Environment Variables

Create `.env` file:

```bash
# API Keys (if needed)
API_KEY=your_api_key_here

# Proxy settings (optional)
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8080
```

## 📚 Examples

### Example 1: Scraping Tables

```bash
# Scrape a Wikipedia table
python main.py scrape https://en.wikipedia.org/wiki/List_of_countries_by_population --element table --format csv
```

### Example 2: Crawling Documentation

```bash
# Crawl Python docs for specific topics
python main.py crawl https://docs.python.org/3/ --keywords "decorator,generator" --element p --max-pages 20
```

### Example 3: Extracting Article Content

```bash
# Extract article paragraphs
python main.py scrape https://example.com/article --element p --format md
```

### Example 4: Custom CSS Selectors

```bash
# Extract specific divs
python main.py scrape https://example.com --element "div.post-content" --format txt

# Extract code blocks
python main.py scrape https://example.com/tutorial --element "pre.code" --format txt
```

## 🛠️ Troubleshooting

### Common Issues

#### SSL Certificate Errors
```bash
# Disable SSL verification (not recommended for production)
python main.py scrape https://example.com --no-ssl-verify
```

#### Rate Limiting Errors
- Increase delay in `config/settings.yaml`
- Use `--delay` flag to add custom delays

#### Memory Issues with Large Pages
- Use streaming mode for large files
- Limit the number of elements extracted

#### Permission Denied Errors
- Check robots.txt compliance
- Verify you have write permissions to the Data/ folder

### Debug Mode

Run with debug flag for detailed output:
```bash
python main.py --debug scrape https://example.com
```

## 🧪 Development

### Project Structure

```
master-data-scraper/
├── core/               # Core scraping modules
│   ├── scraper.py     # Base scraper class
│   ├── parser.py      # HTML parsing
│   ├── crawler.py     # Web crawling
│   └── async_scraper.py # Async scraping
├── utils/             # Utility modules
│   ├── cli.py        # CLI interface
│   ├── rate_limiter.py # Rate limiting
│   └── validators.py  # Input validation
├── config/           # Configuration files
├── Data/            # Scraped data (auto-created)
├── Sports/          # Sports-specific scrapers
└── docs/           # Documentation
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=utils

# Run specific test file
pytest tests/test_scraper.py
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings to all functions
- Keep functions focused and small

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Luke Fournier**

## 🙏 Acknowledgments

- Built with [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- Uses [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Powered by [aiohttp](https://docs.aiohttp.org/) for async operations

## 📞 Support

If you encounter any issues or have questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Search existing [GitHub Issues](https://github.com/yourusername/master-data-scraper/issues)
3. Create a new issue with detailed information about your problem

---

**Happy Scraping! 🕷️**