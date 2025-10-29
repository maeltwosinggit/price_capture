#!/usr/bin/env python3
"""
Samsung Price Capture Script
Fetches product prices from Samsung Malaysia API and updates Google Sheets.
"""

import json
import os
import ssl
import certifi
from datetime import datetime
from typing import List, Dict, Optional

import requests
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables from .env file if running locally
try:
    from dotenv import load_dotenv
    # Only load .env if not running in GitHub Actions
    if not os.environ.get('GITHUB_ACTIONS'):
        load_dotenv()
        print("Loaded environment variables from .env file (local environment)")
        
        # Configure SSL for local environment to handle corporate firewalls/proxies
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Monkey patch requests to disable SSL verification globally for local environment
        import requests.adapters
        import requests.sessions
        
        # Save original methods
        _original_send = requests.adapters.HTTPAdapter.send
        _original_request = requests.sessions.Session.request
        
        def _patched_send(self, request, **kwargs):
            kwargs['verify'] = False
            return _original_send(self, request, **kwargs)
        
        def _patched_request(self, method, url, **kwargs):
            kwargs['verify'] = False
            return _original_request(self, method, url, **kwargs)
        
        # Apply patches
        requests.adapters.HTTPAdapter.send = _patched_send
        requests.sessions.Session.request = _patched_request
        
        print("Configured SSL settings for local environment (globally disabled SSL verification)")
    else:
        print("Running in GitHub Actions - using default SSL settings")
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    print("Environment variables will only be available from system environment.")


class SamsungPriceFetcher:
    """Fetcher for Samsung product prices via API."""
    
    # Constants for API requests
    RESPONSE_PREVIEW_LENGTH = 200
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the fetcher with configuration."""
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
                # Check for placeholder values
                sheet_id = config.get('google_sheet_id', '')
                env_sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
                
                if sheet_id and sheet_id.upper().startswith('YOUR_'):
                    # Only warn if environment variable is also not set
                    if not env_sheet_id:
                        print(f"Warning: Google Sheet ID appears to be a placeholder: {sheet_id}")
                        print("Please configure a valid Google Sheet ID in config.json or set GOOGLE_SHEET_ID environment variable")
                    # Use environment variable instead of placeholder
                    config['google_sheet_id'] = env_sheet_id
                
                return config
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
        
        # Set up headers to mimic a real browser
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://shop.samsung.com/my/',
            'Origin': 'https://shop.samsung.com',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        for product_code in product_codes:
            try:
                # Build API URL with product code
                url = f"{api_endpoint}?productCodes={product_code}"
                print(f"Fetching: {product_code}")
                
                # Make API request with browser-like headers
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Check if response is JSON
                content_type = response.headers.get('content-type', '')
                if 'application/json' not in content_type.lower():
                    # Show a snippet of the response for debugging
                    try:
                        response_snippet = (response.text[:self.RESPONSE_PREVIEW_LENGTH] 
                                          if len(response.text) > self.RESPONSE_PREVIEW_LENGTH 
                                          else response.text)
                    except (TypeError, AttributeError):
                        response_snippet = "[Unable to read response]"
                    print(f"  ✗ {product_code}: API returned non-JSON response (Content-Type: {content_type})")
                    print(f"     Response preview: {response_snippet}")
                    products.append({
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'product_code': product_code,
                        'price': 'N/A',
                        'price_formatted': 'N/A',
                        'stock_status': 'Error: Non-JSON response'
                    })
                    continue
                
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
        
        # Check if running in GitHub Actions
        is_github_actions = bool(os.environ.get('GITHUB_ACTIONS'))
        
        # Try to get credentials from environment variable first
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        
        if creds_json:
            # Credentials from environment variable (GitHub Actions or local .env)
            try:
                import json
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                env_source = "GitHub Actions environment" if is_github_actions else "local .env file"
                print(f"Using Google credentials from {env_source}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in GOOGLE_CREDENTIALS environment variable: {e}")
        else:
            # Fallback to service account file (local only)
            creds_file = 'service_account.json'
            if os.path.exists(creds_file):
                creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
                print(f"Using Google credentials from {creds_file}")
            else:
                # Provide helpful error message based on environment
                if is_github_actions:
                    raise FileNotFoundError(
                        "Google credentials not found in GitHub Actions environment. "
                        "Please set the GOOGLE_CREDENTIALS secret in your repository settings."
                    )
                else:
                    raise FileNotFoundError(
                        "Google credentials not found. Please either:\n"
                        "  1. Add GOOGLE_CREDENTIALS to your .env file, or\n"
                        "  2. Place service_account.json in the project directory\n"
                        f"Current working directory: {os.getcwd()}"
                    )
        
        # Create gspread client
        self.client = gspread.authorize(creds)
        
        # Log which environment we're using
        if is_github_actions:
            print("Using default gspread client for GitHub Actions")
        else:
            print("Using gspread client with SSL verification disabled for local environment")
    
    def update_sheet(self, products: List[Dict[str, str]]):
        """Update Google Sheet with product data."""
        if not products:
            print("No products to update")
            return
        
        try:
            self._authenticate()
            
            sheet_id = self.config.get('google_sheet_id') or os.environ.get('GOOGLE_SHEET_ID')
            
            # Validate sheet ID
            if not sheet_id:
                raise ValueError(
                    "Google Sheet ID not provided. Please set it in config.json or "
                    "as GOOGLE_SHEET_ID environment variable."
                )
            
            if sheet_id.upper().startswith('YOUR_'):
                raise ValueError(
                    f"Google Sheet ID appears to be a placeholder: '{sheet_id}'. "
                    "Please configure a valid Google Sheet ID in config.json or "
                    "set GOOGLE_SHEET_ID environment variable."
                )
            
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
            
        except gspread.exceptions.SpreadsheetNotFound as e:
            print(f"Error: Google Sheet not found (404)")
            print(f"Sheet ID: {sheet_id}")
            print("Possible causes:")
            print("  1. The Google Sheet ID is incorrect")
            print("  2. The sheet has not been shared with the service account")
            print("  3. The sheet was deleted")
            print("\nPlease verify:")
            print("  - The GOOGLE_SHEET_ID is correct")
            print("  - The Google Sheet is shared with your service account email")
            raise
        except Exception as e:
            print(f"Error updating Google Sheet: {e}")
            raise


def main():
    """Main function to run the price capture process."""
    # Detect environment
    is_github_actions = bool(os.environ.get('GITHUB_ACTIONS'))
    environment = "GitHub Actions" if is_github_actions else "Local"
    
    print("=" * 50)
    print("Samsung Price Capture - Starting")
    print(f"Environment: {environment}")
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
