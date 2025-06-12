# Stealth Mode Guide

Master Data Scraper now includes advanced anti-detection features to help bypass rate limiting and anti-bot measures.

## Overview

The stealth mode implements multiple techniques to make your scraper appear more human-like:

1. **User-Agent Rotation** - Cycles through real browser user agents
2. **Human Behavior Simulation** - Adds realistic delays and browsing patterns
3. **Smart Headers** - Generates browser-specific headers
4. **Session Management** - Maintains cookies and referrer chains
5. **Adaptive Delays** - Adjusts timing based on server responses

## Quick Start

Stealth mode is enabled by default. Just run the scraper normally:

```bash
python main.py
```

## Configuration

Edit `config/stealth.yaml` to customize behavior:

```yaml
stealth:
  enabled: true  # Toggle stealth mode
  user_agent_rotation:
    rotate_after_requests: 10  # Rotate UA every N requests

human_behavior:
  delays:
    min_delay: 1.0  # Minimum seconds between requests
    max_delay: 5.0  # Maximum delay
```

## Domain-Specific Settings

For sites with strict rate limits, add custom delays:

```yaml
rate_limit_handling:
  domain_specific:
    example.com:
      min_delay: 3.0
      max_delay: 10.0
      rotate_ua_always: true
```

## Features in Action

### 1. Automatic Rate Limit Handling

When encountering a 429 error, the scraper will:
- Rotate to a new user agent
- Wait with exponential backoff
- Take a "human break" before retrying

### 2. Human-Like Browsing

The scraper simulates human behavior by:
- Reading at realistic speeds (250 WPM)
- Taking random short breaks
- Having longer breaks after many requests
- Varying request patterns

### 3. Smart Request Headers

Headers are generated to match the browser:
- Chrome headers for Chrome user agents
- Consistent Accept-Language
- Proper referrer chains

## Monitoring

View stealth statistics:

```bash
python main.py stealth-stats
```

This shows:
- Total requests made
- Domains visited
- Current user agent
- Average response times

## Best Practices

1. **Start Slow**: Begin with default settings and adjust if needed
2. **Respect Robots.txt**: Stealth mode doesn't bypass legal restrictions
3. **Monitor Performance**: Use stealth-stats to track behavior
4. **Adjust Per Domain**: Some sites need longer delays than others

## Troubleshooting

### Still Getting Rate Limited?

1. Increase delays in `config/domains.yaml`:
   ```yaml
   rate_limits:
     problem-site.com: 10.0  # 10 seconds between requests
   ```

2. Enable more aggressive rotation:
   ```yaml
   user_agent_rotation:
     rotate_after_requests: 1  # New UA every request
   ```

3. Take longer breaks:
   ```yaml
   breaks:
     long_break_duration: [60, 300]  # 1-5 minute breaks
   ```

### Scraping Too Slow?

Reduce delays for trusted sites:
```yaml
domain_specific:
  trusted-site.com:
    min_delay: 0.5
    max_delay: 1.0
```

## Ethical Considerations

- Always respect website terms of service
- Don't overload servers even if you can bypass limits
- Use scraped data responsibly
- Consider reaching out to site owners for API access

## Advanced Features

### Custom Profiles

Create browsing personalities in `config/stealth.yaml`:

```yaml
profiles:
  fast_reader: 0.1     # Speed reader
  normal_reader: 0.6   # Average user
  slow_reader: 0.3     # Careful reader
```

### Time-Based Patterns

Enable realistic time-of-day patterns:

```yaml
time_patterns:
  enabled: true
  peak_hours: [9, 17]  # More active 9 AM - 5 PM
```

## Command Examples

```bash
# Scrape with stealth mode
python main.py scrape https://example.com --element table

# Crawl with human-like behavior
python main.py crawl https://example.com --keywords "data" --max-pages 50

# View current statistics
python main.py stealth-stats

# Clear cache to start fresh
python main.py clear-cache
```

Remember: The goal is to be respectful while getting the data you need!