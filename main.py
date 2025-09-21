from fastapi import FastAPI
from typing import Optional
from scraper import scrape_fda_website

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/scrape")
def scrape_data(device_name: str, product_code: Optional[str] = None, since: Optional[int] = 2020):
    """
    Scrapes the FDA's TPLC device search page for device and patient problems.
    """
    data = scrape_fda_website(device_name, product_code, since)
    return data
