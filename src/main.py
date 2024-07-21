from fastapi import FastAPI, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import time
import redis
import json
from dotenv import load_dotenv
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Construct the path to the .env file
env_path = os.path.join(project_root, '.env')

# For Loading environment variables from the .env file
load_dotenv(dotenv_path=env_path)


base_dir = os.path.dirname(os.path.abspath(__file__))

scrape_dir = os.path.dirname(base_dir)


json_file_path = os.path.join(scrape_dir, 'data_json', 'scraped_products.json')


API_TOKEN = os.getenv("API_TOKEN")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")






# Pydantic models
class Product(BaseModel):
    product_title: str
    product_price: str
    path_to_image: str

class ScrapeResponse(BaseModel):
    products: List[Product]

class Notifier(ABC):
    @abstractmethod
    def notify(self, message: str):
        pass

class ConsoleNotifier(Notifier):
    def notify(self, message: str):
        print(message)

class Scraper:
    def __init__(self, base_url: str, notifier: Notifier, redis_client, retries: int = 3, delay: int = 5, json_file_path: str = 'scraped_products.json'):
        self.base_url = base_url
        self.notifier = notifier
        self.redis_client = redis_client
        self.retries = retries
        self.delay = delay
        self.json_file_path = json_file_path

    def fetch_page(self, url: str, proxies: Optional[dict] = None):
        for attempt in range(self.retries):
            try:
                response = requests.get(url, proxies=proxies)
                response.raise_for_status()
                return response.content
            except RequestException as e:
                if attempt < self.retries - 1:
                    time.sleep(self.delay)
                else:
                    raise e

    def parse_page(self, content: str) -> List[Product]:
        soup = BeautifulSoup(content, "html.parser")
        products = soup.find_all("div", class_="product-inner")
        results = []

        for product in products:
            name = product.find("h2", class_="woo-loop-product__title").text.strip()
            price = product.find("span", class_="woocommerce-Price-amount").text.strip()
            image = product.find("img", class_="attachment-woocommerce_thumbnail")["src"].strip()
            
            results.append(Product(product_title=name, product_price=price, path_to_image=image))

        return results

    def cache_product(self, product: Product):
        product_key = f"product:{product.product_title}"
        cached_product = self.redis_client.get(product_key)
        
        if cached_product:
            cached_product = json.loads(cached_product)
            if cached_product['product_price'] == product.product_price:
                return False  # No update needed

        self.redis_client.set(product_key, json.dumps(product.dict()))
        return True  # Product updated

    def save_to_json(self, products: List[Product]):
        directory = os.path.dirname(self.json_file_path)
        
        # Checking the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        # Saving to the JSON file
        with open(self.json_file_path, 'w') as file:
            json.dump([product.dict() for product in products], file, indent=4)

    def scrape(self, limit_pages: Optional[int] = None, proxy: Optional[str] = None) -> List[Product]:
        results = []
        proxies = {"http": proxy, "https": proxy} if proxy else None

        for page in range(1, (limit_pages or 10) + 1):  # Scrape up to 10 pages by default
            url = self.base_url.format(page)
            content = self.fetch_page(url, proxies)
            page_results = self.parse_page(content)
            
            for product in page_results:
                if self.cache_product(product):
                    results.append(product)

            if limit_pages and page >= limit_pages:
                break
        
        self.save_to_json(results)

        self.notifier.notify(f"Scraped {len(results)} products.")
        return results

app = FastAPI()
notifier = ConsoleNotifier()
redis_client = redis.Redis(host=REDIS_HOST,
                           port=REDIS_PORT,
                           password=REDIS_PASSWORD)

scraper = Scraper(base_url="https://dentalstall.com/shop/page/{}/", notifier=notifier, redis_client=redis_client, json_file_path=json_file_path)

def get_current_user(token: str = Query(...)):
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    return token

@app.get("/scrape", response_model=ScrapeResponse)
def scrape_website(limit_pages: Optional[int] = Query(None, alias="limit-pages"), 
                   proxy: Optional[str] = Query(None),
                   token: str = Depends(get_current_user)):
    products = scraper.scrape(limit_pages=limit_pages, proxy=proxy)
    return ScrapeResponse(products=products)
