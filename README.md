# Master Data Scraper

A powerful Python command-line application for web scraping with an intuitive interface.

## Features

- **Interactive CLI**: Guided command-line interface for easy web scraping
- **Multiple Formats**: Export data as CSV, JSON, Markdown, or plain text
- **Domain Organization**: Automatically organizes scraped data by source domain
- **Ethical Scraping**: Built-in rate limiting and robots.txt compliance
- **Rich Terminal UI**: Beautiful terminal output with colors and progress indicators

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Step-by-step Installation

```bash
# Clone the repository
git clone https://github.com/lukefournier/master-data-scraper.git
cd master-data-scraper

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install the package and dependencies
pip install -r requirements.txt

# For development, also install dev dependencies
pip install -r requirements-dev.txt

# Or install as an editable package with all dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Check that the main script runs
python main.py --version

# Or use the installed command
scraper --help
```

## Quick Start

```bash
# Run the scraper
python main.py

# Or use the installed command
scraper
```

## Usage

The application will guide you through the process:

1. Enter the URL you want to scrape
2. Select the HTML element type (table, h1, p, li, etc.)
3. Choose your output format (csv, json, md, txt)
4. Your data will be saved in the `Data/` folder, organized by domain

## Development

This project is under active development. See [docs/TASKS.md](docs/TASKS.md) for the implementation roadmap and [docs/PRD.md](docs/PRD.md) for detailed requirements.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Luke Fournier