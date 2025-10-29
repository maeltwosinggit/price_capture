# Quick Setup Guide

## What You Need to Provide for Google Sheets Integration

### 1. Google Service Account Credentials (JSON file)

**Steps to get this:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or use existing one
3. Enable "Google Sheets API" and "Google Drive API"
4. Create a Service Account (APIs & Services > Credentials > Create Credentials > Service Account)
5. Download the JSON key file

**This JSON file contains:**
- Service account email (e.g., `your-bot@project.iam.gserviceaccount.com`)
- Private key for authentication
- Project information

**Where to add it:**
- GitHub: Repository Settings > Secrets > Actions > New secret named `GOOGLE_CREDENTIALS`
- Copy the **entire JSON file content** as the secret value

---

### 2. Google Sheet ID

**Steps to get this:**
1. Create a Google Sheet at [sheets.google.com](https://sheets.google.com)
2. **IMPORTANT**: Share it with your service account email (found in the JSON file)
   - Click "Share" button
   - Add the service account email
   - Give it "Editor" permission
3. Copy the Sheet ID from the URL

**Example URL:**
```
https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j/edit
                                      ^^^^^^^^^^^^^^^^^^^^
                                      This is your Sheet ID
```

**Where to add it:**
- GitHub: Repository Settings > Secrets > Actions > New secret named `GOOGLE_SHEET_ID`
- Paste just the Sheet ID (not the full URL)

---

## Complete Checklist

- [ ] Created Google Cloud Project
- [ ] Enabled Google Sheets API
- [ ] Enabled Google Drive API
- [ ] Created Service Account
- [ ] Downloaded Service Account JSON key
- [ ] Created Google Sheet for storing prices
- [ ] Shared Google Sheet with service account email (with Editor permission)
- [ ] Copied Sheet ID from URL
- [ ] Added `GOOGLE_CREDENTIALS` secret to GitHub repository
- [ ] Added `GOOGLE_SHEET_ID` secret to GitHub repository
- [ ] Tested the workflow (optional: manual trigger from Actions tab)

---

## Example Service Account Email

After creating a service account, you'll get an email like:
```
price-capture-bot@my-project-12345.iam.gserviceaccount.com
```

**Remember to share your Google Sheet with this email!** Otherwise, the script won't be able to write data to your sheet.

---

## Security Notes

⚠️ **Keep your service account JSON file secure!**
- Never commit it to GitHub
- Never share it publicly
- It's already in `.gitignore` for safety

✅ The GitHub secrets are encrypted and only accessible during workflow runs.

---

## Need Help?

If you encounter issues:
1. Check that both secrets are set correctly in GitHub
2. Verify the Google Sheet is shared with the service account email
3. Check the Actions tab for detailed error logs
4. Ensure APIs are enabled in Google Cloud Console
