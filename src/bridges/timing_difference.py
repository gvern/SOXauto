import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import sys

# --- CONFIGURATION ---
# Update these values with your specific details
GSHEET_NAME = "Name of the Google Sheet Islam Shared"
VOUCHERS_WORKSHEET_NAME = "Name of the Tab with Voucher Data"
USAGE_WORKSHEET_NAME = "Name of the Tab with Gdash Usage Data" # Or keep as CSV if it's a separate file
CREDENTIALS_FILE = "data/credentials/credentials.json" # Your Google service account key file
OUTPUT_FILE = "data/outputs/timing_difference_bridge_september.csv"

# --- 1. Load the Data from Google Sheets ---
def load_data():
    """Authenticates with Google and loads data from the specified Google Sheet."""
    try:
        # Authenticate with Google using the service account credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet and the specific worksheets
        spreadsheet = client.open(GSHEET_NAME)
        
        print(f"Loading data from worksheet: '{VOUCHERS_WORKSHEET_NAME}'...")
        vouchers_worksheet = spreadsheet.worksheet(VOUCHERS_WORKSHEET_NAME)
        vouchers_df = get_as_dataframe(vouchers_worksheet)
        
        print(f"Loading data from worksheet: '{USAGE_WORKSHEET_NAME}'...")
        usage_worksheet = spreadsheet.worksheet(USAGE_WORKSHEET_NAME)
        usage_df = get_as_dataframe(usage_worksheet)
        
        print("Data loaded successfully from Google Sheets.")
        return vouchers_df, usage_df
        
    except FileNotFoundError:
        print(f"Error: Credentials file '{CREDENTIALS_FILE}' not found. Please follow setup instructions.")
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet '{GSHEET_NAME}' not found. Check the name and sharing settings.")
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound as e:
        print(f"Error: {e}. One of the worksheets was not found in the spreadsheet.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

# --- 2. Prepare the Data ---
def prepare_data(vouchers_df, usage_df):
    """Cleans and prepares the dataframes for analysis."""
    # !!! IMPORTANT: Update these column names to match the actual names in your Google Sheet !!!
    try:
        vouchers_df['order_date'] = pd.to_datetime(vouchers_df['order_date_column_name'], errors='coerce')
        usage_df['delivery_date'] = pd.to_datetime(usage_df['delivery_date_column_name'], errors='coerce')
        usage_df['cancellation_date'] = pd.to_datetime(usage_df['cancellation_date_column_name'], errors='coerce')
        return vouchers_df, usage_df
    except KeyError as e:
        print(f"Error: Column not found - {e}. Please update the column names in the 'prepare_data' function.")
        sys.exit(1)

# --- 3. Apply the Business Logic ---
def find_timing_difference_vouchers(vouchers_df, usage_df):
    """Identifies vouchers that represent a timing difference."""
    # Filter for non-marketing vouchers used in Nigeria in September 2025
    september_vouchers = vouchers_df[
        (vouchers_df['country'].str.lower() == 'nigeria') &
        (vouchers_df['business_use'].str.lower() == 'store credit') &
        (vouchers_df['order_date'].dt.month == 9) &
        (vouchers_df['order_date'].dt.year == 2025)
    ]
    print(f"Found {len(september_vouchers)} non-marketing vouchers used in Nigeria in September 2025.")

    # Find the usage details for these specific vouchers
    september_usage = usage_df[usage_df['voucher_id'].isin(september_vouchers['voucher_id'])]

    # Identify vouchers with a timing difference (delivered or cancelled in October)
    timing_difference_vouchers = september_usage[
        (september_usage['delivery_date'].dt.month == 10) |
        (september_usage['cancellation_date'].dt.month == 10)
    ]
    print(f"Identified {len(timing_difference_vouchers)} vouchers with a timing difference.")
    return timing_difference_vouchers

# --- 4. Output the Result ---
def output_results(timing_difference_vouchers):
    """Saves the results to a CSV file."""
    if not timing_difference_vouchers.empty:
        print("\n--- Vouchers with Timing Difference ---")
        # !!! IMPORTANT: Update these column names if needed !!!
        output_columns = ['voucher_id', 'order_id', 'amount', 'delivery_date', 'cancellation_date']
        print(timing_difference_vouchers[output_columns])
        
        timing_difference_vouchers.to_csv(OUTPUT_FILE, index=False, columns=output_columns)
        print(f"\nResults saved to {OUTPUT_FILE}")
    else:
        print("No vouchers with a timing difference were found.")

if __name__ == "__main__":
    vouchers_df, usage_df = load_data()
    vouchers_df, usage_df = prepare_data(vouchers_df, usage_df)
    timing_difference_vouchers = find_timing_difference_vouchers(vouchers_df, usage_df)
    output_results(timing_difference_vouchers)
