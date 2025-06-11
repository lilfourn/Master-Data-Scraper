# PURPOSE: Master Data Scraper

## 🚀 Introduction

**Master Data Scraper** is a powerful and elegant Python command-line application designed to make web scraping simple and efficient. Built for those who live in the terminal, it provides a rich, interactive experience that guides you through the process of extracting data from any URL. It's the perfect tool for developers, data analysts, and researchers who need to quickly gather information from the web without ever leaving their keyboard.

---

## ✨ Key Features

- **Interactive CLI:** A guided, friendly command-line interface that prompts for each necessary input, making the scraping process intuitive.
- **Flexible Data Selection:** Precisely target the data you need by specifying HTML elements like tables (`<table>`), headings (`<h1>`, `<h2>`), paragraphs (`<p>`), list items (`<li>`), or any other valid HTML tag.
- **Multiple Output Formats:** Save your scraped data in several popular formats to fit your workflow:
  - Comma-Separated Values (`.csv`)
  - Markdown (`.md`)
  - JSON (`.json`)
  - Plain Text (`.txt`)
- **Organized Data Storage:** All output is automatically saved into a unified `Data/` folder. The app creates a clear, predictable file structure, so your data is always easy to find and manage.
- **Enhanced Terminal UI:** Utilizes modern terminal styling to improve readability with colored output, clear separators, and status indicators.

---

## ⚙️ How It Works: A Terminal Walkthrough

The application is designed to be run directly from your terminal. It initiates a session that walks you through the entire process from start to finish.

1.  **Initiate the Scraper:**
    You start the application with a simple Python command.

    ```sh
    python main.py
    ```

2.  **Enter the Target URL:**
    The application greets you and asks for the webpage you want to scrape.

    ```
    Welcome to Master Data Scraper!
    [?] Please enter the full URL you wish to scrape:
    > [https://en.wikipedia.org/wiki/List_of_S%26P_500_companies](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies)
    ```

3.  **Select the HTML Element:**
    Next, you're prompted to specify the type of data you want to extract.

    ```
    [?] What type of HTML data do you want to extract? (e.g., table, h1, p, li):
    > table
    ```

4.  **Choose the Output Format:**
    Finally, select your desired file format from a list of options.

    ```
    [?] In what format would you like to save the data? (csv, md, json, txt):
    > csv
    ```

5.  **Scrape and Save:**
    The application provides real-time feedback, confirming the action and informing you once the data is saved.

    ```
    [INFO] Scraping <table> elements from [https://en.wikipedia.org/wiki/List_of_S%26P_500_companies](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies)...
    [SUCCESS] Data saved successfully!
    [PATH] Your file is located at: Data/2025-06-11_en-wikipedia-org_tables.csv
    ```

---

## 📂 Output Organization

A core principle of this tool is keeping your data tidy. All generated files are stored in a top-level directory named `Data`. The file naming convention is designed to be intuitive and informative, typically including the date, the source domain, and the type of data scraped.

For example, running the scraper as shown above would result in the following directory structure:
