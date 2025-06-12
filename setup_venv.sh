#!/bin/bash
# Setup script for Master Data Scraper virtual environment

echo "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

echo ""
echo "✅ Virtual environment setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "In VS Code:"
echo "1. Press Cmd+Shift+P"
echo "2. Select 'Python: Select Interpreter'"
echo "3. Choose './venv/bin/python'"