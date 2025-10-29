#!/usr/bin/env python3
"""
Simple tests for price_capture.py improvements
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from price_capture import SamsungPriceFetcher, GoogleSheetsUpdater


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading with placeholder detection."""
    
    def test_placeholder_detection_in_config(self):
        """Test that placeholder Google Sheet IDs are detected and replaced."""
        # Create a temporary config file with placeholder
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            # Load config - should detect placeholder and use env var instead
            fetcher = SamsungPriceFetcher(temp_config)
            
            # Sheet ID should be empty (since env var is not set) instead of placeholder
            self.assertEqual(fetcher.config.get('google_sheet_id'), "")
        finally:
            os.unlink(temp_config)
    
    def test_placeholder_with_env_var_set(self):
        """Test that placeholder is replaced with env var without warning."""
        # Create a temporary config file with placeholder
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            # Set environment variable
            os.environ['GOOGLE_SHEET_ID'] = 'real_sheet_id_123'
            
            # Load config - should use env var without warning
            fetcher = SamsungPriceFetcher(temp_config)
            
            # Sheet ID should be from env var
            self.assertEqual(fetcher.config.get('google_sheet_id'), 'real_sheet_id_123')
        finally:
            # Clean up
            if 'GOOGLE_SHEET_ID' in os.environ:
                del os.environ['GOOGLE_SHEET_ID']
            os.unlink(temp_config)
    
    def test_valid_config_loading(self):
        """Test that valid configs are loaded correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "1234567890abcdef",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            fetcher = SamsungPriceFetcher(temp_config)
            
            # Sheet ID should remain as configured
            self.assertEqual(fetcher.config.get('google_sheet_id'), "1234567890abcdef")
            self.assertEqual(fetcher.config.get('api_endpoint'), "https://test.api.com")
        finally:
            os.unlink(temp_config)


class TestGoogleSheetsValidation(unittest.TestCase):
    """Test Google Sheets ID validation."""
    
    def test_placeholder_sheet_id_rejected(self):
        """Test that placeholder Sheet IDs are rejected with clear error."""
        config = {
            "google_sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE",
            "worksheet_name": "Prices"
        }
        
        updater = GoogleSheetsUpdater(config)
        products = [{'timestamp': '2025-10-29', 'product_code': 'TEST'}]
        
        with patch.object(updater, '_authenticate'):
            with self.assertRaises(ValueError) as context:
                updater.update_sheet(products)
            
            # Check error message mentions placeholder
            self.assertIn("placeholder", str(context.exception).lower())
    
    def test_missing_sheet_id_rejected(self):
        """Test that missing Sheet IDs are rejected with clear error."""
        config = {
            "google_sheet_id": "",
            "worksheet_name": "Prices"
        }
        
        updater = GoogleSheetsUpdater(config)
        products = [{'timestamp': '2025-10-29', 'product_code': 'TEST'}]
        
        with patch.object(updater, '_authenticate'):
            with self.assertRaises(ValueError) as context:
                updater.update_sheet(products)
            
            # Check error message is helpful
            self.assertIn("not provided", str(context.exception).lower())


class TestAPIResponseHandling(unittest.TestCase):
    """Test improved API response handling."""
    
    @patch('price_capture.requests.get')
    def test_browser_headers_sent(self, mock_get):
        """Test that browser-like headers are sent with API requests."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "resultCode": "0000",
            "productDatas": [{
                "promotionPrice": 999.99,
                "promotionPriceFormatted": "RM 999.99",
                "stockLevelStatusDisplay": "In Stock"
            }]
        }
        mock_get.return_value = mock_response
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            fetcher = SamsungPriceFetcher(temp_config)
            products = fetcher.fetch_prices()
            
            # Verify headers were passed
            call_args = mock_get.call_args
            self.assertIn('headers', call_args.kwargs)
            headers = call_args.kwargs['headers']
            
            # Check for key headers
            self.assertIn('User-Agent', headers)
            self.assertIn('Mozilla', headers['User-Agent'])
            self.assertIn('Accept', headers)
            self.assertEqual(headers['Accept'], 'application/json, text/plain, */*')
        finally:
            os.unlink(temp_config)
    
    @patch('price_capture.requests.get')
    def test_non_json_response_handling(self, mock_get):
        """Test that non-JSON responses are handled gracefully."""
        # Mock a response with HTML content
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            fetcher = SamsungPriceFetcher(temp_config)
            products = fetcher.fetch_prices()
            
            # Should have one product with error status
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0]['product_code'], 'TEST123')
            self.assertIn('Non-JSON', products[0]['stock_status'])
        finally:
            os.unlink(temp_config)
    
    @patch('price_capture.requests.get')
    def test_json_response_with_valid_data(self, mock_get):
        """Test that valid JSON responses are parsed correctly."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "resultCode": "0000",
            "productDatas": [{
                "promotionPrice": 999.99,
                "promotionPriceFormatted": "RM 999.99",
                "stockLevelStatusDisplay": "In Stock"
            }]
        }
        mock_get.return_value = mock_response
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "api_endpoint": "https://test.api.com",
                "product_codes": ["TEST123"],
                "google_sheet_id": "",
                "worksheet_name": "Prices"
            }
            json.dump(config_data, f)
            temp_config = f.name
        
        try:
            fetcher = SamsungPriceFetcher(temp_config)
            products = fetcher.fetch_prices()
            
            # Should have one product with valid data
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0]['product_code'], 'TEST123')
            self.assertEqual(products[0]['price'], 999.99)
            self.assertEqual(products[0]['price_formatted'], 'RM 999.99')
        finally:
            os.unlink(temp_config)


if __name__ == '__main__':
    unittest.main()
