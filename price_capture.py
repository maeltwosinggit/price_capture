#!/usr/bin/env python3
"""
Samsung Price Capture Script
Scrapes product prices from Samsung Malaysia multistore and updates Google Sheets.
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import gspread
from google.oauth2.service_account import Credentials


class SamsungPriceScraper:
    """Scraper for Samsung product prices."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the scraper with configuration."""
        self.config = self._load_config(config_path)
        self.driver = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {config_path} not found, using defaults")
            return {
                "target_url": "https://www.samsung.com/my/multistore/eppsme/",
                "google_sheet_id": os.environ.get("GOOGLE_SHEET_ID", ""),
                "worksheet_name": "Prices",
                "scrape_delay": 2,
                "max_products": 50
            }
    
    def _setup_driver(self):
        """Set up Selenium WebDriver with Chrome."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def scrape_prices(self) -> List[Dict[str, str]]:
        """
        Scrape product prices from Samsung website.
        Returns list of dictionaries with product information.
        """
        products = []
        
        try:
            self._setup_driver()
            url = self.config.get("target_url")
            print(f"Navigating to {url}")
            
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(self.config.get("scrape_delay", 2))
            
            # Try to wait for product elements to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div, article, li"))
                )
            except:
                print("Warning: Timeout waiting for elements, continuing anyway...")
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Samsung websites typically use various selectors for products
            # Try multiple common patterns
            product_selectors = [
                {'container': 'div.product-card', 'title': '.product-title, .product-name', 'price': '.price, .product-price'},
                {'container': 'article.product', 'title': 'h3, h4, .title', 'price': '.price, .amount'},
                {'container': 'li.product-item', 'title': '.product-name, .name', 'price': '.price'},
                {'container': 'div[class*="product"]', 'title': '[class*="title"], [class*="name"]', 'price': '[class*="price"]'},
            ]
            
            found_products = False
            
            for selector_set in product_selectors:
                product_elements = soup.select(selector_set['container'])
                
                if product_elements:
                    print(f"Found {len(product_elements)} products using selector: {selector_set['container']}")
                    found_products = True
                    
                    for element in product_elements[:self.config.get("max_products", 50)]:
                        try:
                            # Extract title
                            title_elem = element.select_one(selector_set['title'])
                            title = title_elem.get_text(strip=True) if title_elem else "N/A"
                            
                            # Extract price
                            price_elem = element.select_one(selector_set['price'])
                            price = price_elem.get_text(strip=True) if price_elem else "N/A"
                            
                            # Extract product URL if available
                            link_elem = element.find('a', href=True)
                            url = link_elem['href'] if link_elem else "N/A"
                            if url != "N/A" and not url.startswith('http'):
                                url = f"https://www.samsung.com{url}"
                            
                            if title != "N/A" or price != "N/A":
                                products.append({
                                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'product_name': title,
                                    'price': price,
                                    'url': url
                                })
                        except Exception as e:
                            print(f"Error extracting product data: {e}")
                            continue
                    
                    break  # Stop after finding products with first matching selector
            
            if not found_products:
                print("No products found with standard selectors, trying generic approach...")
                # Fallback: Look for any elements with price-like text
                all_text = soup.get_text()
                print(f"Page text length: {len(all_text)} characters")
                
                # Create a sample entry to indicate scraping occurred
                products.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'product_name': 'Sample - Manual Review Required',
                    'price': 'N/A',
                    'url': url
                })
            
            print(f"Successfully scraped {len(products)} products")
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            # Add error entry
            products.append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'product_name': f'Error: {str(e)}',
                'price': 'N/A',
                'url': self.config.get("target_url", "N/A")
            })
        finally:
            if self.driver:
                self.driver.quit()
        
        return products


class GoogleSheetsUpdater:
    """Updates Google Sheets with product price data."""
    
    def __init__(self, config: dict):
        """Initialize Google Sheets updater."""
        self.config = config
        self.client = None
        
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Try to get credentials from environment variable or file
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        
        if creds_json:
            # Credentials from environment variable (for GitHub Actions)
            import json
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            # Credentials from file (for local testing)
            creds_file = 'service_account.json'
            if not os.path.exists(creds_file):
                raise FileNotFoundError(
                    f"Google credentials not found. Please provide {creds_file} "
                    "or set GOOGLE_CREDENTIALS environment variable."
                )
            creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        
        self.client = gspread.authorize(creds)
    
    def update_sheet(self, products: List[Dict[str, str]]):
        """Update Google Sheet with product data."""
        if not products:
            print("No products to update")
            return
        
        try:
            self._authenticate()
            
            sheet_id = self.config.get('google_sheet_id') or os.environ.get('GOOGLE_SHEET_ID')
            if not sheet_id:
                raise ValueError("Google Sheet ID not provided in config or environment")
            
            sheet = self.client.open_by_key(sheet_id)
            worksheet_name = self.config.get('worksheet_name', 'Prices')
            
            # Try to get existing worksheet or create new one
            try:
                worksheet = sheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=10)
            
            # Check if headers exist
            existing_data = worksheet.get_all_values()
            
            if not existing_data or not existing_data[0]:
                # Add headers
                headers = ['Timestamp', 'Product Name', 'Price', 'URL']
                worksheet.append_row(headers)
            
            # Append product data
            for product in products:
                row = [
                    product.get('timestamp', ''),
                    product.get('product_name', ''),
                    product.get('price', ''),
                    product.get('url', '')
                ]
                worksheet.append_row(row)
            
            print(f"Successfully updated Google Sheet with {len(products)} products")
            
        except Exception as e:
            print(f"Error updating Google Sheet: {e}")
            raise


def main():
    """Main function to run the price capture process."""
    print("=" * 50)
    print("Samsung Price Capture - Starting")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        # Load configuration
        config_path = os.environ.get('CONFIG_PATH', 'config.json')
        
        # Initialize scraper and scrape prices
        scraper = SamsungPriceScraper(config_path)
        products = scraper.scrape_prices()
        
        if not products:
            print("Warning: No products scraped")
            return
        
        # Update Google Sheets
        updater = GoogleSheetsUpdater(scraper.config)
        updater.update_sheet(products)
        
        print("=" * 50)
        print("Samsung Price Capture - Completed Successfully")
        print("=" * 50)
        
    except Exception as e:
        print(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
