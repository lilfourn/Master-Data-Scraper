# Scraping Customization Guide

This guide explains the new customization features in Master Data Scraper v1.0.0.

## Table of Contents
- [Scraping Options](#scraping-options)
- [File Naming Conventions](#file-naming-conventions)
- [Command Line Usage](#command-line-usage)
- [Configuration File](#configuration-file)
- [Examples](#examples)

## Scraping Options

### What Can Be Customized?

You can now control exactly what data gets scraped and saved:

| Option | Default | Description |
|--------|---------|-------------|
| `scrape_metadata` | true | Extract page title, meta tags, language, etc. |
| `scrape_scripts` | false | Include `<script>` elements in the data |
| `scrape_styles` | false | Include `<style>` elements in the data |
| `scrape_headers` | true | Extract h1-h6 header information |
| `scrape_images` | false | Extract image src, alt, and title attributes |
| `scrape_comments` | false | Include HTML comments |
| `include_attributes` | true | Include element attributes (class, id, etc.) |
| `include_page_info` | true | Add page metadata to saved files |
| `clean_whitespace` | true | Remove extra whitespace from text |

### Interactive Mode

When running in interactive mode (`python main.py`), you'll be asked:
```
Would you like to customize scraping options? [y/N]
```

If you choose yes, you can toggle each option individually.

### Command Line Flags

Control options directly from the command line:

```bash
# Skip metadata extraction
python main.py scrape https://example.com --no-metadata

# Include scripts and styles
python main.py scrape https://example.com --include-scripts --include-styles

# Include image information
python main.py scrape https://example.com --include-images
```

## File Naming Conventions

### Naming Templates

Create custom filename patterns using placeholders:

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{timestamp}` | Full timestamp | 20240111_143052 |
| `{date}` | Date only | 20240111 |
| `{time}` | Time only | 143052 |
| `{year}` | Year | 2024 |
| `{month}` | Month | 01 |
| `{day}` | Day | 11 |
| `{hour}` | Hour | 14 |
| `{minute}` | Minute | 30 |
| `{second}` | Second | 52 |
| `{domain}` | Website domain | example_com |
| `{element}` | Element type | table |
| `{title}` | Page title (first 50 chars) | Home_Page |
| `{slug}` | URL path as slug | products_category_items |
| `{custom}` | Custom name if provided | my_custom_name |

### Template Examples

```yaml
# Simple timestamp and element
naming_template: '{timestamp}_{element}'
# Result: 20240111_143052_table.csv

# Date with descriptive title
naming_template: '{date}_{title}_{element}'
# Result: 20240111_Home_Page_table.csv

# Full information
naming_template: '{domain}_{slug}_{element}_{date}'
# Result: example_com_products_items_table_20240111.csv

# Human-friendly
naming_template: '{year}-{month}-{day}_{hour}{minute}_{title}'
# Result: 2024-01-11_1430_Home_Page.csv
```

### Command Line Usage

```bash
# Use custom naming template
python main.py scrape https://example.com \
  --naming-template "{date}_{title}_{element}"

# Quick options
python main.py scrape https://example.com \
  --use-title \    # Include page title
  --use-domain     # Include domain name
```

## Configuration File

Create a `config/settings.yaml` file to set defaults:

```yaml
# Scraping customization
scraping_customization:
  scrape_metadata: true
  scrape_scripts: false
  scrape_styles: false
  scrape_headers: true
  scrape_images: true
  include_attributes: true
  include_page_info: true
  clean_whitespace: true

# File naming
file_naming:
  naming_template: '{date}_{title}_{element}'
  naming_date_format: '%Y%m%d_%H%M%S'
  naming_max_length: 100
  naming_use_url_slug: false
```

## Examples

### Example 1: News Article Scraping

Extract article content with metadata:

```bash
python main.py scrape https://news.example.com/article \
  --element p \
  --include-images \
  --naming-template "{date}_{title}" \
  --format md
```

Result:
- Filename: `20240111_Breaking_News_Story.md`
- Contains: Paragraphs, images, and page metadata

### Example 2: Data Table Extraction

Extract tables without extra content:

```bash
python main.py scrape https://data.example.com/stats \
  --element table \
  --no-metadata \
  --naming-template "{domain}_{element}_{timestamp}"
```

Result:
- Filename: `data_example_com_table_20240111_143052.csv`
- Contains: Only table data, no metadata

### Example 3: Full Page Archive

Archive complete page with all elements:

```bash
python main.py scrape https://example.com \
  --element "*" \
  --include-scripts \
  --include-styles \
  --include-images \
  --naming-template "{date}_full_archive_{domain}"
```

### Example 4: Using Configuration File

1. View current configuration:
```bash
python main.py config
```

2. Create/update configuration file when prompted

3. All future scraping will use your custom defaults

## Interactive Mode Features

In interactive mode, you'll see new options:

1. **Customize Scraping Options**: Toggle what data to extract
2. **Customize Filename**: Set naming template and options

These settings are applied for the current session. To make them permanent, update your `config/settings.yaml` file.

## Tips

1. **Performance**: Disabling metadata extraction (`--no-metadata`) speeds up scraping
2. **Storage**: Excluding scripts/styles significantly reduces file sizes
3. **Organization**: Use domain and date in filenames for better organization
4. **Compliance**: Always respect robots.txt and rate limits

## Troubleshooting

**Issue**: Filenames are too long
- Solution: Reduce `naming_max_length` in settings
- Use shorter templates without {title} or {slug}

**Issue**: Missing metadata
- Solution: Ensure `scrape_metadata: true` in settings
- Don't use `--no-metadata` flag

**Issue**: Special characters in filenames
- Solution: The sanitizer automatically replaces invalid characters with underscores

For more help, run `python main.py --help` or check the main documentation.