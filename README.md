# Samsung Price Capture Automation

Automated daily price capture from Samsung Malaysia API with Google Sheets integration.

## Features

- 🤖 **Automated price fetching** via Samsung API
- 📊 **Google Sheets integration** for data storage
- ⏰ **Daily automation** via GitHub Actions
- 🔄 **Manual trigger** support for on-demand runs
- 💰 **Tracks promotion prices** for multiple Samsung products

## Prerequisites

- Python 3.11 or higher
- Google Cloud Platform account (free tier is sufficient)
- A Google Sheet to store the data

## Google Sheets Setup Requirements

### Step 1: Create a Google Cloud Project and Enable APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable the following APIs:
   - **Google Sheets API**
   - **Google Drive API**
   
   To enable APIs:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and click "Enable"
   - Search for "Google Drive API" and click "Enable"

### Step 2: Create a Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the details:
   - **Service account name**: `price-capture-bot` (or any name you prefer)
   - **Service account description**: `Service account for automated price capture`
4. Click "Create and Continue"
5. Skip the optional role assignment (click "Continue")
6. Click "Done"

### Step 3: Generate Service Account Key

1. In the "Credentials" page, find your service account
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" > "Create new key"
5. Select **JSON** format
6. Click "Create"
7. **Save the downloaded JSON file securely** - this contains your credentials

The JSON file will look like this:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "price-capture-bot@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Step 4: Create and Share Google Sheet

1. Create a new Google Sheet at [sheets.google.com](https://sheets.google.com)
2. Name it something like "Samsung Price Tracking"
3. **Important**: Share the sheet with your service account email
   - Click the "Share" button in the top-right
   - Add the service account email (found in the JSON file as `client_email`)
   - Example: `price-capture-bot@your-project.iam.gserviceaccount.com`
   - Give it **Editor** permissions
   - Uncheck "Notify people" (it's a service account, not a real person)
   - Click "Share"
4. Copy the **Sheet ID** from the URL
   - The URL looks like: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
   - Copy the `SHEET_ID_HERE` part

### Step 5: Configure GitHub Secrets

You need to provide two secrets to the GitHub repository:

1. **GOOGLE_CREDENTIALS**: The entire content of the service account JSON file
   - Go to your repository on GitHub
   - Navigate to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name: `GOOGLE_CREDENTIALS`
   - Value: Copy and paste the **entire content** of the JSON file you downloaded
   - Click "Add secret"

2. **GOOGLE_SHEET_ID**: Your Google Sheet ID
   - Click "New repository secret" again
   - Name: `GOOGLE_SHEET_ID`
   - Value: Paste the Sheet ID you copied from the URL
   - Click "Add secret"

## Installation & Local Testing

### 1. Clone the repository
```bash
git clone https://github.com/maeltwosinggit/price_capture.git
cd price_capture
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure for local testing

For local testing, you have two options:

**Option A: Use service account JSON file**
- Place your `service_account.json` file in the project root
- Update `config.json` with your Sheet ID:
```json
{
  "google_sheet_id": "YOUR_SHEET_ID_HERE"
}
```

**Option B: Use environment variables**
```bash
export GOOGLE_CREDENTIALS='{"type":"service_account",...}'
export GOOGLE_SHEET_ID='your_sheet_id_here'
```

### 4. Run the script
```bash
python price_capture.py
```

## GitHub Actions Automation

The workflow runs automatically:
- **Daily at 00:00 UTC** (8:00 AM Malaysia Time)
- Can also be triggered manually from the "Actions" tab

### Manual Trigger
1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Daily Price Capture" workflow
4. Click "Run workflow"

## Configuration

Edit `config.json` to customize:

```json
{
  "api_endpoint": "https://shop.samsung.com/my/multistore/my_epp/eppsme/servicesv2/getSimpleProductsInfo",
  "product_codes": [
    "F-AR1-0BYFAMWK",
    "F-AR4-0F09D0AM",
    "F-AR1-8BYFAMWK",
    "F-AR2-4BYFAMWK",
    "F-AR1-0BYEAAWK",
    "F-AR1-3BYEAAWK",
    "F-AR-18BYEAAWK",
    "F-AR2-4BYEAAWK",
    "F-AR1-0AYHZBWK",
    "F-AR1-3AYHZBWK",
    "RT62K7005BS/ME"
  ],
  "google_sheet_id": "YOUR_GOOGLE_SHEET_ID_HERE",
  "worksheet_name": "Prices"
}
```

- **api_endpoint**: Samsung API endpoint for product information
- **product_codes**: List of Samsung product codes to track
- **google_sheet_id**: Your Google Sheet ID (can also be set via environment variable)
- **worksheet_name**: Name of the worksheet tab (will be created if doesn't exist)

## Output Format

The Google Sheet will be populated with the following columns:

| Timestamp | Product Code | Price | Price Formatted | Stock Status |
|-----------|--------------|-------|-----------------|--------------|
| 2025-10-29 08:00:00 | F-AR4-0F09D0AM | 989.45 | RM 989.45 | In Stock |
| 2025-10-29 08:00:00 | RT62K7005BS/ME | 2599.00 | RM 2,599.00 | In Stock |

## Troubleshooting

### "Google credentials not found" error
- Ensure `GOOGLE_CREDENTIALS` secret is set correctly in GitHub
- For local testing, ensure `service_account.json` exists or environment variable is set

### "Permission denied" on Google Sheet
- Make sure you shared the Google Sheet with the service account email
- Check that the service account has Editor permissions

### No products fetched
- Check if the API endpoint is accessible
- Verify product codes are correct in `config.json`
- Check the GitHub Actions logs for detailed error messages
- The script will create entries with error information for failed products

### Workflow not running
- Check that GitHub Actions is enabled for your repository
- Verify the cron schedule in `.github/workflows/daily_price_capture.yml`

## Summary: What You Need to Provide

✅ **Google Cloud Service Account JSON** (set as `GOOGLE_CREDENTIALS` secret)
✅ **Google Sheet ID** (set as `GOOGLE_SHEET_ID` secret)
✅ **Share your Google Sheet** with the service account email

That's it! Once these are configured, the automation will run daily.