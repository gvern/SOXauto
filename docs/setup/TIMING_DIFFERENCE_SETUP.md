# Timing Difference Bridge - Setup Guide

This guide will help you set up and run the `src/bridges/timing_difference.py` script to identify vouchers with timing differences between order and delivery/cancellation dates.

---

## 📋 Prerequisites

1. **Python 3.11+** installed
2. **Google Cloud Service Account** with access to Google Sheets API
3. **Access to the Google Sheet** that Islam shared
4. **Required Python packages** (see below)

---

## 🔧 Step-by-Step Setup

### 1. Install Dependencies

First, install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- `pandas` - Data manipulation
- `gspread` - Google Sheets API client
- `gspread-dataframe` - Convert sheets to DataFrames
- `oauth2client` - OAuth2 authentication
- `google-auth` and related packages - Google authentication

---

### 2. Get Your Google Service Account Credentials

You need a `credentials.json` file from Google Cloud:

#### Option A: If you already have a service account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Find your service account
4. Click on it and go to the **Keys** tab
5. Click **Add Key** → **Create New Key** → **JSON**
6. Download the JSON file and rename it to `credentials.json`

#### Option B: Create a new service account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. Enter a name (e.g., "SOXauto-Sheets-Reader")
6. Click **Create and Continue**
7. Skip role assignment (click **Continue**)
8. Click **Done**
9. Click on the new service account
10. Go to the **Keys** tab
11. Click **Add Key** → **Create New Key** → **JSON**
12. Download the JSON file and rename it to `credentials.json`

---

### 3. Enable Google Sheets API

Make sure the Google Sheets API is enabled for your project:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Library**
3. Search for "Google Sheets API"
4. Click on it and click **Enable**

---

### 4. Share the Google Sheet with Your Service Account

**⚠️ CRITICAL STEP - The script won't work without this!**

1. Open the `credentials.json` file in a text editor
2. Find the `"client_email"` field - it looks like:
   ```
   "client_email": "soxauto-sheets-reader@your-project.iam.gserviceaccount.com"
   ```
3. Copy this email address
4. Open the Google Sheet that Islam shared with you
5. Click the **Share** button (top right)
6. Paste the service account email
7. Give it **Viewer** or **Editor** access
8. Click **Send** (uncheck "Notify people" if asked)

---

### 5. Configure the Script

Open `src/bridges/timing_difference.py` (or run it with CLI flags) and update the configuration section at the top or pass overrides on the command line:

```python
# --- CONFIGURATION ---
GSHEET_NAME = "Name of the Google Sheet Islam Shared"  # UPDATE THIS
VOUCHERS_WORKSHEET_NAME = "Name of the Tab with Voucher Data"  # UPDATE THIS
USAGE_WORKSHEET_NAME = "Name of the Tab with Gdash Usage Data"  # UPDATE THIS
CREDENTIALS_FILE = "data/credentials/credentials.json"  # Place credentials in data/credentials/
OUTPUT_FILE = "data/outputs/timing_difference_bridge_september.csv"
```

**Important:** The names must match exactly as they appear in Google Sheets (case-sensitive).

---

### 6. Update Column Names

You need to update the column names in the script to match the actual column names in your Google Sheet:

#### In the `prepare_data()` function (around line 60):
```python
vouchers_df['order_date'] = pd.to_datetime(vouchers_df['order_date_column_name'], errors='coerce')
usage_df['delivery_date'] = pd.to_datetime(usage_df['delivery_date_column_name'], errors='coerce')
usage_df['cancellation_date'] = pd.to_datetime(usage_df['cancellation_date_column_name'], errors='coerce')
```

Replace `'order_date_column_name'`, `'delivery_date_column_name'`, and `'cancellation_date_column_name'` with the actual column names from your sheets.

#### In the `find_timing_difference_vouchers()` function (around line 75):
Check and update these column names if needed:
- `'country'`
- `'business_use'`
- `'voucher_id'`

#### In the `output_results()` function (around line 100):
Update the output columns list if the column names are different:
```python
output_columns = ['voucher_id', 'order_id', 'amount', 'delivery_date', 'cancellation_date']
```

---

## 🚀 Running the Script

Once everything is configured (or if you have a local Excel extract), place the Excel file in the project `Bridge_source/` folder and run the script from the project root. Example invocation (this mirrors what we used successfully):

```bash
# Example: run using the provided Excel file in Bridge_source with explicit headers and column mappings
python3 -m src.bridges.timing_difference \
   --file "Bridge_source/All Countries - Sep.25 - Voucher TV Extract.xlsx" \
   --issued "Issuance" --usage "Usage" --expiration "Expiration" \
   --issued-header 9 --usage-header 7 --expiration-header 9 \
   --voucher-id-col id --order-id-col Transaction_No --business-use-col business_use \
   --amount-col "Total Used" --country-col ID_COMPANY --inactive-date-col "Inactive at" \
   --order-date-col created_at --country-filter EC_NG
```

### Expected Output

```
Loading data from worksheet: 'Voucher Data'...
Loading data from worksheet: 'Gdash Usage'...
Data loaded successfully from Google Sheets.
Found 1543 non-marketing vouchers used in Nigeria in September 2025.
Identified 87 vouchers with a timing difference.

--- Vouchers with Timing Difference ---
   voucher_id  order_id    amount delivery_date cancellation_date
0  VCH123456   ORD789012  15000.0    2025-10-05               NaT
1  VCH234567   ORD890123  25000.0    2025-10-12               NaT
...

Results saved to `data/outputs/timing_difference_bridge_september.csv` (script will create the folder if missing).
```

---

## 🐛 Troubleshooting

### Error: "Credentials file not found"
- Make sure `credentials.json` is in `data/credentials/` folder
- Check the `CREDENTIALS_FILE` variable points to `data/credentials/credentials.json`

### Error: "Spreadsheet not found"
- Check that `GSHEET_NAME` matches exactly (including case)
- Make sure you shared the sheet with the service account email

### Error: "Worksheet not found"
- Check that `VOUCHERS_WORKSHEET_NAME` and `USAGE_WORKSHEET_NAME` match exactly
- Tab names are case-sensitive

### Error: "Column not found"
- Open the Google Sheet and check the exact column names
- Update the column names in `prepare_data()` and `find_timing_difference_vouchers()` functions
- Make sure there are no leading/trailing spaces in column names

### No vouchers found
- Check the filter criteria in `find_timing_difference_vouchers()`
- Verify that the date columns are being parsed correctly
- Try printing the first few rows of the dataframes to inspect the data

---

## 📊 Output File

The script generates `data/outputs/timing_difference_bridge_september.csv` containing:
- `voucher_id` - The voucher identifier
- `order_id` - The associated order
- `amount` - The voucher amount
- `delivery_date` - When the order was delivered (if in October)
- `cancellation_date` - When the order was cancelled (if in October)

---

## 🎯 Next Steps for Tomorrow's Meeting

1. **Run the script** and generate the CSV
2. **Review the results** - check a few voucher IDs manually to validate
3. **Prepare to demo** - have the script ready to run live
4. **Discuss with Islam**:
   - "Does this list match your manual analysis?"
   - "Is the logic complete, or are there edge cases?"
   - "What's the next bridge we should tackle?"

   ---

   ## 📌 What changed (quick)

   - The script was renamed/moved during refactor: the active entry point is now `src/bridges/timing_difference.py` (run with `python3 -m src.bridges.timing_difference`).
   - For ad-hoc runs you can drop the downloaded Excel into the repository `Bridge_source/` folder and call the script with `--file` and header/column overrides (example shown above).
   - The script will create `data/outputs/` for the CSV result.

   __Doc updated to reflect current repository structure and local-excel workflow.__

---

## 📝 Notes

- The script filters for **Nigeria** only and **non-marketing vouchers** (store credit)
- It looks for orders placed in **September 2025**
- It identifies timing differences when delivery/cancellation is in **October 2025**
- You can modify these filters in the `find_timing_difference_vouchers()` function

---

**Good luck with your demo tomorrow! 🚀**
