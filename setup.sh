#!/bin/bash

# Setup script for Master Data Scraper
# This script creates a virtual environment and installs all dependencies

echo "🚀 Master Data Scraper Setup"
echo "=========================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.8 or higher is required. You have $python_version"
    exit 1
fi

echo "✅ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📈 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Ask if dev dependencies should be installed
read -p "Install development dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛠️  Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔐 Creating .env file from template..."
    cp .env.example .env
fi

# Create Data directory if it doesn't exist
if [ ! -d "Data" ]; then
    echo "📁 Creating Data directory..."
    mkdir -p Data
    touch Data/.gitkeep
fi

# Create _logs directory
if [ ! -d "Data/_logs" ]; then
    echo "📝 Creating logs directory..."
    mkdir -p Data/_logs
    touch Data/_logs/.gitkeep
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the scraper:"
echo "  python main.py"
echo ""
echo "Happy scraping! 🕷️"