# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Master Data Scraper is a Python command-line application for web scraping. The project is currently in early development with empty implementation files.

## Project Structure

- `/Data/` - Directory for storing scraped data output
- `/Sports/` - Contains sport-specific scrapers (NBA, NFL, NHL, WNBA)
  - Each subdirectory has an empty `main.py` file
- `/docs/` - Project documentation
  - `PURPOSE.md` - Comprehensive project documentation
  - `PRD.md` - Product Requirements Document
  - `TASKS.md` - Implementation task list
- `/config/` - Configuration files (to be populated)
- `main.py` - Main entry point for the application
- `requirements.txt` - Currently empty, dependencies need to be added
- `setup.py` & `setup.cfg` - Package configuration
- `LICENSE` - MIT License
- `README.md` - Project overview and quick start guide

## Key Features to Implement

According to PURPOSE.md, this application should:
1. Provide an interactive CLI interface for web scraping
2. Support scraping various HTML elements (tables, h1, p, li, etc.)
3. Export data in multiple formats (CSV, MD, JSON, TXT)
4. Save data to the Data/ folder with naming convention: `YYYY-MM-DD_domain_element-type.format`
5. Include colored terminal output and status indicators

## Development Commands

Since the project is in early development, standard Python commands should be used:

```bash
# Run the main scraper (once implemented)
python main.py

# Install dependencies (once requirements.txt is populated)
pip install -r requirements.txt
```

## Implementation Notes

1. The main entry point (`main.py`) has been created in the root directory
2. Dependencies are specified in `requirements.txt` and `setup.py`
3. The Sport-specific scrapers in `/Sports/` subdirectories appear to be separate implementations
4. All scraped data should be saved to the `/Data/` directory with appropriate naming
5. All scraped data should be saved organized based on their domain in the Data folder
6. Project uses Click for CLI and Rich for terminal UI
7. Documentation is organized in `/docs/` directory
8. Configuration files will be placed in `/config/` directory

## Architecture Considerations

- The application should follow the interactive flow described in PURPOSE.md
- Consider implementing a modular structure with separate modules for:
  - URL input and validation
  - HTML parsing and element extraction
  - Data formatting and export
  - Terminal UI and user interaction

## Workflow Reminders

- When we complete a task, please mark it as complete in @docs/TASKS.md