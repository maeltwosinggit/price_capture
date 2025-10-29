#!/usr/bin/env python3
"""
Samsung Price Capture Script
Fetches product prices from Samsung Malaysia API and updates Google Sheets.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

import requests
import gspread
from google.oauth2.service_account import Credentials


class SamsungPriceFetcher:
    """Fetcher for Samsung product prices via API."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the fetcher with configuration."""
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {config_path} not found, using defaults")
            return {
                "api_endpoint": "https://shop.samsung.com/my/multistore/my_epp/eppsme/servicesv2/getSimpleProductsInfo",
                "product_codes": [],
                "google_sheet_id": os.environ.get("GOOGLE_SHEET_ID", ""),
                "worksheet_name": "Prices"
            }
    
    def fetch_prices(self) -> List[Dict[str, str]]:
        """
        Fetch product prices from Samsung API.
        Returns list of dictionaries with product information.
        """
        products = []
        api_endpoint = self.config.get("api_endpoint")
        product_codes = self.config.get("product_codes", [])
        
        if not product_codes:
            print("Warning: No product codes configured")
            return products
        
        print(f"Fetching prices for {len(product_codes)} products...")
        
        for product_code in product_codes:
            try:
                # Build API URL with product code
                url = f"{api_endpoint}?productCodes={product_code}"
                print(f"Fetching: {product_code}")
                
                # Make API request
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                
                # Extract product data
                if data.get("resultCode") == "0000" and data.get("productDatas"):
                    product_data = data["productDatas"][0]
                    
                    # Extract promotion price (or regular price if no promotion)
                    promotion_price = product_data.get("promotionPrice")
                    regular_price = product_data.get("price")
                    price = promotion_price if promotion_price else regular_price
                    
                    # Get formatted price
                    price_formatted = product_data.get("promotionPriceFormatted") or product_data.get("priceFormatted", "N/A")
                    
                    # Get stock status
                    stock_status = product_data.get("stockLevelStatusDisplay", "Unknown")
                    
                    products.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'product_code': product_code,
                        'price': price,
                        'price_formatted': price_formatted,
                        'stock_status': stock_status
                    })
                    
                    print(f"  ✓ {product_code}: {price_formatted} ({stock_status})")
                else:
                    print(f"  ✗ {product_code}: No data or error in response")
                    products.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'product_code': product_code,
                        'price': 'N/A',
                        'price_formatted': 'N/A',
                        'stock_status': 'Error: No data'
                    })
                    
            except requests.exceptions.RequestException as e:
                print(f"  ✗ {product_code}: Request error - {e}")
                products.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'product_code': product_code,
                    'price': 'N/A',
                    'price_formatted': 'N/A',
                    'stock_status': f'Error: {str(e)}'
                })
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"  ✗ {product_code}: Parse error - {e}")
                products.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'product_code': product_code,
                    'price': 'N/A',
                    'price_formatted': 'N/A',
                    'stock_status': f'Error: Parse error'
                })
        
        print(f"\nSuccessfully fetched {len(products)} products")
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
                headers = ['Timestamp', 'Product Code', 'Price', 'Price Formatted', 'Stock Status']
                worksheet.append_row(headers)
            
            # Append product data
            for product in products:
                row = [
                    product.get('timestamp', ''),
                    product.get('product_code', ''),
                    str(product.get('price', '')),
                    product.get('price_formatted', ''),
                    product.get('stock_status', '')
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
        
        # Initialize fetcher and fetch prices
        fetcher = SamsungPriceFetcher(config_path)
        products = fetcher.fetch_prices()
        
        if not products:
            print("Warning: No products fetched")
            return
        
        # Update Google Sheets
        updater = GoogleSheetsUpdater(fetcher.config)
        updater.update_sheet(products)
        
        print("=" * 50)
        print("Samsung Price Capture - Completed Successfully")
        print("=" * 50)
        
    except Exception as e:
        print(f"Fatal error in main: {e}")
        raise


if __name__ == "__main__":
    main()
