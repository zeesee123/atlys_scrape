# Scraper Project

## Overview
This project is a web scraper built using FastAPI that extracts product information from an online store and stores it in a JSON file. It supports configurable settings such as limiting the number of pages to scrape and using a proxy.

## Setup Instructions

### Prerequisites
- Python 3.8+
- Redis (for caching)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/zeesee123/atlys_scrape.git

### Navigate to the project directory:

1. cd scrape

### Install dependencies:


1. pip install fastapi
2. pip install pydantic
3. pip install requests
4. pip install beautifulsoup4
5. pip install redis
6. pip install python-dotenv


### Rename and configure the environment file:

1. Rename .env.example to .env:
2. mv .env.example .env
3. Edit the .env file to include your environment-specific variables (e.g., API keys, database URLs).


### Data Storage(db)

The scraped product data is stored in a JSON file located at data_json/scraped_products.json in the root directory of the project.


### Run the project 

1. uvicorn src.main:app --reload
**(Make sure you are inside the src folder when running this command.)**
       