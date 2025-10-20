import os
import sys
import argparse
import pandas as pd

# --- CONFIGURATION (can be overridden via env or CLI) ---
# 1) Path to the downloaded Excel file (update this)
VOUCHER_EXTRACT_FILE = os.getenv(
    "VOUCHER_EXTRACT_FILE",
    "path/to/your/downloaded/All Countries - Sep.25 - Voucher TV Extract.xlsx"
)

# 2) Exact worksheet (tab) names
ISSUED_WORKSHEET_NAME = os.getenv("ISSUED_WORKSHEET_NAME", "Voucher Issued")
USAGE_WORKSHEET_NAME = os.getenv("USAGE_WORKSHEET_NAME", "Voucher Usage")

# 3) Output CSV
OUTPUT_FILE = os.getenv("TIMING_DIFF_OUTPUT", "data/outputs/timing_difference_bridge_september.csv")
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Timing Difference Bridge from Excel extract")
    parser.add_argument("--file", dest="file", default=VOUCHER_EXTRACT_FILE, help="Path to Excel file")
    parser.add_argument("--issued", dest="issued", default=ISSUED_WORKSHEET_NAME, help="Issued/Used by Order Date sheet name")
    parser.add_argument("--usage", dest="usage", default=USAGE_WORKSHEET_NAME, help="Usage by Delivery Date sheet name")
    parser.add_argument("--output", dest="output", default=OUTPUT_FILE, help="Output CSV path")
    # Optional header rows (0-indexed in pandas read_excel)
    parser.add_argument("--issued-header", dest="issued_header", type=int, default=None, help="Header row index for Issued sheet")
    parser.add_argument("--usage-header", dest="usage_header", type=int, default=None, help="Header row index for Usage sheet")
    # Optional expiration sheet for cancellation dates
    parser.add_argument("--expiration", dest="expiration", default=os.getenv("EXPIRATION_SHEET", ""), help="Expiration sheet name (optional)")
    parser.add_argument("--expiration-header", dest="expiration_header", type=int, default=None, help="Header row index for Expiration sheet")
    parser.add_argument("--inactive-date-col", dest="inactive_date_col", default=os.getenv("INACTIVE_DATE_COL", "Inactive at"))
    # Column mappings (override as needed)
    parser.add_argument("--order-date-col", dest="order_date_col", default=os.getenv("ORDER_DATE_COL", "order_creation_date"))
    parser.add_argument("--delivery-date-col", dest="delivery_date_col", default=os.getenv("DELIVERY_DATE_COL", "delivered_date"))
    parser.add_argument("--cancellation-date-col", dest="cancellation_date_col", default=os.getenv("CANCELLATION_DATE_COL", "cancelled_date"))
    parser.add_argument("--country-col", dest="country_col", default=os.getenv("COUNTRY_COL", "country"))
    parser.add_argument("--country-filter", dest="country_filter", default=os.getenv("COUNTRY_FILTER", "nigeria"), help="Country filter value (e.g., 'nigeria' or 'ng')")
    parser.add_argument("--business-use-col", dest="business_use_col", default=os.getenv("BUSINESS_USE_COL", "business_use"))
    parser.add_argument("--voucher-id-col", dest="voucher_id_col", default=os.getenv("VOUCHER_ID_COL", "voucher_id"))
    parser.add_argument("--order-id-col", dest="order_id_col", default=os.getenv("ORDER_ID_COL", "order_id"))
    parser.add_argument("--amount-col", dest="amount_col", default=os.getenv("AMOUNT_COL", "amount"))
    return parser.parse_args()


# --- 1. Load the Data from the Excel File ---
def load_data(xlsx_path: str, issued_sheet: str, usage_sheet: str,
              issued_header: int | None,
              usage_header: int | None,
              expiration_sheet: str | None,
              expiration_header: int | None):
    """Loads data from the specified Excel worksheets."""
    try:
        print(f"Loading data from worksheet: '{issued_sheet}'...")
        issued_df = pd.read_excel(
            xlsx_path,
            sheet_name=issued_sheet,
            engine="openpyxl",
            header=issued_header
        )

        print(f"Loading data from worksheet: '{usage_sheet}'...")
        usage_df = pd.read_excel(
            xlsx_path,
            sheet_name=usage_sheet,
            engine="openpyxl",
            header=usage_header
        )

        print("Data loaded successfully from Excel file.")
        expiration_df = None
        if expiration_sheet:
            print(f"Loading data from worksheet: '{expiration_sheet}' (optional)...")
            try:
                expiration_df = pd.read_excel(
                    xlsx_path,
                    sheet_name=expiration_sheet,
                    engine="openpyxl",
                    header=expiration_header
                )
            except Exception as e:
                print(f"Warning: Could not load expiration sheet '{expiration_sheet}': {e}")
        return issued_df, usage_df, expiration_df

    except FileNotFoundError:
        print(f"Error: File not found at '{xlsx_path}'. Please update the path.")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: One of the worksheets was not found. Please check the names: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


# --- 2. Prepare the Data ---
def prepare_data(issued_df: pd.DataFrame, usage_df: pd.DataFrame, expiration_df: pd.DataFrame | None, *,
                 order_date_col: str,
                 delivery_date_col: str,
                 cancellation_date_col: str,
                 voucher_id_col: str,
                 order_id_col: str,
                 inactive_date_col: str):
    """Cleans and prepares the dataframes for analysis."""
    # Update these column names to match the actual names in your file
    try:
        # Guesses below; adjust after inspecting the file
        # Order date from issuance
        issued_df['order_date'] = pd.to_datetime(issued_df[order_date_col], errors='coerce')

        # Delivery date: prefer explicit column; else try derive from Transaction_No like 'TYYMMDD...'
        if delivery_date_col in usage_df.columns:
            usage_df['delivery_date'] = pd.to_datetime(usage_df[delivery_date_col], errors='coerce')
        else:
            if order_id_col in usage_df.columns:
                # Extract YYMMDD after leading 'T'
                def parse_txn_date(val):
                    try:
                        s = str(val)
                        if len(s) >= 8 and s[0].upper() == 'T' and s[1:7].isdigit():
                            y, m, d = s[1:3], s[3:5], s[5:7]
                            year = int('20' + y)
                            return pd.Timestamp(year=int(year), month=int(m), day=int(d))
                    except Exception:
                        return pd.NaT
                    return pd.NaT
                usage_df['delivery_date'] = usage_df[order_id_col].apply(parse_txn_date)
            else:
                usage_df['delivery_date'] = pd.NaT

        # Cancellation date: prefer explicit column; else attempt from expiration sheet join
        if cancellation_date_col in usage_df.columns:
            usage_df['cancellation_date'] = pd.to_datetime(usage_df[cancellation_date_col], errors='coerce')
        else:
            usage_df['cancellation_date'] = pd.NaT
            if expiration_df is not None and inactive_date_col in expiration_df.columns:
                try:
                    exp = expiration_df[[voucher_id_col, inactive_date_col]].copy()
                    exp.columns = [voucher_id_col, 'cancellation_date']
                    exp['cancellation_date'] = pd.to_datetime(exp['cancellation_date'], errors='coerce')
                    usage_df = usage_df.merge(exp, on=voucher_id_col, how='left', suffixes=("", "_exp"))
                except Exception as e:
                    print(f"Warning: Could not merge expiration dates: {e}")
        return issued_df, usage_df
    except KeyError as e:
        print(f"Error: Column not found - {e}. Please update the column names in the 'prepare_data' function.")
        sys.exit(1)


# --- 3. Apply the Business Logic ---
def find_timing_difference_vouchers(issued_df: pd.DataFrame, usage_df: pd.DataFrame, *,
                                    country_col: str,
                                    business_use_col: str,
                                    voucher_id_col: str,
                                    country_filter: str):
    """Identifies vouchers that represent a timing difference."""
    # Filter for non-marketing vouchers used in Nigeria in September 2025
    # Normalize country matching: accept 'nigeria', 'ng', or values ending with '_ng'
    cf = str(country_filter).lower()
    def is_country_match(val):
        v = str(val).lower()
        return (cf in v) or v.endswith(f"_{cf}") or v.endswith("_ng") or v == cf

    base_mask = (
        issued_df[country_col].apply(is_country_match) &
        (issued_df['order_date'].dt.month == 9) &
        (issued_df['order_date'].dt.year == 2025)
    )
    # Apply business use filter if the column exists in issued_df
    if business_use_col in issued_df.columns:
        bu_mask = issued_df[business_use_col].astype(str).str.lower().str.replace(' ', '_') == 'store_credit'
        mask = base_mask & bu_mask
    else:
        mask = base_mask
    september_vouchers = issued_df[mask]
    print(f"Found {len(september_vouchers)} non-marketing vouchers ordered in Nigeria in September 2025.")

    # Find the usage details for these specific vouchers
    september_usage = usage_df[usage_df[voucher_id_col].isin(september_vouchers[voucher_id_col])]

    # Identify vouchers with a timing difference (delivered or cancelled in October)
    timing_difference_vouchers = september_usage[
        (september_usage['delivery_date'].dt.month == 10) |
        (september_usage['cancellation_date'].dt.month == 10)
    ]
    print(f"Identified {len(timing_difference_vouchers)} vouchers with a timing difference.")
    return timing_difference_vouchers


# --- 4. Output the Result ---
def output_results(timing_difference_vouchers: pd.DataFrame, output_path: str, *,
                   voucher_id_col: str, order_id_col: str, amount_col: str):
    """Saves the results to a CSV file."""
    if not timing_difference_vouchers.empty:
        print("\n--- Vouchers with Timing Difference ---")
        # Update if needed to match available columns
        output_columns = [voucher_id_col, order_id_col, amount_col, 'delivery_date', 'cancellation_date']
        print(timing_difference_vouchers[output_columns].head(20))

        timing_difference_vouchers.to_csv(output_path, index=False, columns=output_columns)
        print(f"\nResults saved to {output_path}")
    else:
        print("No vouchers with a timing difference were found.")


if __name__ == "__main__":
    args = parse_args()
    issued_df, usage_df, expiration_df = load_data(
        args.file,
        args.issued,
        args.usage,
        args.issued_header,
        args.usage_header,
        args.expiration,
        args.expiration_header,
    )
    issued_df, usage_df = prepare_data(
        issued_df,
        usage_df,
        expiration_df,
        order_date_col=args.order_date_col,
        delivery_date_col=args.delivery_date_col,
        cancellation_date_col=args.cancellation_date_col,
        voucher_id_col=args.voucher_id_col,
        order_id_col=args.order_id_col,
        inactive_date_col=args.inactive_date_col,
    )
    timing_difference_vouchers = find_timing_difference_vouchers(
        issued_df, usage_df,
        country_col=args.country_col,
        business_use_col=args.business_use_col,
        voucher_id_col=args.voucher_id_col,
        country_filter=args.country_filter,
    )
    output_results(
        timing_difference_vouchers, args.output,
        voucher_id_col=args.voucher_id_col,
        order_id_col=args.order_id_col,
        amount_col=args.amount_col,
    )
