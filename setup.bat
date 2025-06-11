@echo off
REM Setup script for Master Data Scraper (Windows)
REM This script creates a virtual environment and installs all dependencies

echo Master Data Scraper Setup
echo =========================

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

echo Python found.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Ask for dev dependencies
set /p install_dev="Install development dependencies? (y/n): "
if /i "%install_dev%"=="y" (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
)

REM Create Data directory if it doesn't exist
if not exist Data (
    echo Creating Data directory...
    mkdir Data
    type nul > Data\.gitkeep
)

REM Create _logs directory
if not exist Data\_logs (
    echo Creating logs directory...
    mkdir Data\_logs
    type nul > Data\_logs\.gitkeep
)

echo.
echo Setup complete!
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate
echo.
echo To run the scraper:
echo   python main.py
echo.
echo Happy scraping!
pause