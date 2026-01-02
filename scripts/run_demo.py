# scripts/run_demo.py - FINAL PRESENTATION VERSION
import pandas as pd
import os
import sys
from datetime import datetime
import argparse
from dataclasses import asdict

# --- Ensure project modules are importable ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.bridges import load_rules, classify_bridges

# --- Path Configuration ---
HISTORICAL_DATA_PATH = os.path.join(REPO_ROOT, "tests", "fixtures", "historical_data")
OUTPUT_PATH = os.path.join(REPO_ROOT, "data", "outputs")
os.makedirs(OUTPUT_PATH, exist_ok=True)

# --- Country Code to Name Mapping ---
COUNTRY_MAP = {
    "EC_NG": "Nigeria", "EC_KE": "Kenya", "EC_IC": "Côte d'Ivoire",
    "EC_MA": "Morocco", "HF_SN": "Senegal", "JD_DZ": "Algeria",
    "JD_GH": "Ghana", "JD_UG": "Uganda", "JM_EG": "Egypt",
}

def load_historical_sheet(file_name, sheet_name, header_keyword):
    """Loads a specific sheet from an Excel file, intelligently finding the header row."""
    file_path = os.path.join(HISTORICAL_DATA_PATH, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Historical Excel file is missing: {file_path}")

    temp_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=20, engine='openpyxl')
    
    header_row_index = -1
    for i, row in temp_df.iterrows():
        if row.astype(str).str.strip().str.lower().eq(header_keyword.lower()).any():
            header_row_index = i
            break
            
    if header_row_index == -1:
        raise ValueError(f"Could not find header row with keyword '{header_keyword}' in sheet '{sheet_name}'.")

    df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row_index, engine='openpyxl')
    df.columns = [str(c).strip() for c in df.columns]
    return df

def normalize_for_bridges(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort normalization to prepare data for the bridge classifier."""
    print("   - Normalizing column names for the classification agent...")
    out = df.copy()
    
    column_mapping = {
        'Transaction_Type': ['transaction_type', 'type', 'transaction type'],
        'IS_PREPAYMENT': ['is_prepayment', 'prepayment', 'is prepayment'],
    }
    
    for target_col, source_candidates in column_mapping.items():
        if target_col not in out.columns:
            for candidate in source_candidates:
                for existing_col in out.columns:
                    if candidate == existing_col.lower().strip():
                        out.rename(columns={existing_col: target_col}, inplace=True)
                        print(f"     - INFO: Mapped messy column '{existing_col}' to standard '{target_col}'")
                        break
                if target_col in out.columns:
                    break
    return out

def main():
    parser = argparse.ArgumentParser(description="Run a full offline demo of the SOXauto pipeline.")
    parser.add_argument("--country-code", default="EC_NG", help="The country code for reconciliation (e.g., EC_NG).")
    args = parser.parse_args()
    
    COUNTRY_CODE = args.country_code
    COUNTRY_NAME = COUNTRY_MAP.get(COUNTRY_CODE, "Unknown Country")

    print(f"🚀 Starting SOXauto end-to-end pipeline demonstration for {COUNTRY_NAME} 🚀")

    # --- PHASE 1: SIMULATED EXTRACTION & EVIDENCE GENERATION ---
    print("\n--- Phase 1: Simulating Extraction & Generating Evidence Package ---")
    try:
        ipe_to_demo = "IPE_07"
        ipe_item = get_item_by_id(ipe_to_demo)
        ipe_config_dict = {'id': ipe_item.item_id, 'description': ipe_item.title, 'secret_name': 'N/A_in_demo_mode'}
        
        # Extract country code and period from cutoff date or defaults
        country = COUNTRY_CODE.split('_')[1] if '_' in COUNTRY_CODE else COUNTRY_CODE
        # For period, use current month in YYYYMM format
        period = datetime.now().strftime('%Y%m')
        
        runner = IPERunner(
            ipe_config=ipe_config_dict, 
            secret_manager=None,
            country=country,
            period=period,
            full_params={
                'country_code': COUNTRY_CODE,
                'country_name': COUNTRY_NAME
            }
        )
        
        print(f"   - Loading historical data for {ipe_to_demo} from Excel file...")
        demo_file_name = "2. All Countries Mar-25 - IBSAR - Customer Accounts.xlsx"
        df_ipe07 = load_historical_sheet(demo_file_name, sheet_name="13003", header_keyword="Row Labels")
        
        print("   - Generating Digital Evidence Package (6 files)...")
        runner.run_demo(demo_dataframe=df_ipe07, source_name=f"{demo_file_name}/13003")
        print(f"✅ Evidence Package for {ipe_to_demo} generated successfully.")
    except Exception as e:
        print(f"❌ ERROR in Phase 1: {e}"); import traceback; traceback.print_exc(); sys.exit(1)

    # --- PHASE 2: RECONCILIATION LOGIC SIMULATION ---
    print(f"\n--- Phase 2: Running Reconciliation Logic for {COUNTRY_NAME} ---")
    try:
        print("   - Loading 'Actuals' data from NAV GL Balance sheet...")
        df_actuals_pivot = load_historical_sheet("1. All Countries Mar-25 - IBSAR - Consolidation.xlsx", sheet_name="NAV GLBalance PG", header_keyword="Row Labels")
        actuals_row = df_actuals_pivot[df_actuals_pivot['Row Labels'].astype(str).str.strip().str.lower() == 'grand total']
        actuals_total = pd.to_numeric(actuals_row[COUNTRY_CODE].iloc[0], errors='coerce')
        print(f"   - Total 'Actuals': {actuals_total:,.2f}")

        print("   - Loading 'Targets' data from various IPE sheets...")
        df_customers = load_historical_sheet("2. All Countries Mar-25 - IBSAR - Customer Accounts.xlsx", sheet_name="13003", header_keyword="Row Labels")
        target_customers = pd.to_numeric(df_customers[df_customers['Row Labels'] == COUNTRY_CODE]['Sum of Grand Total'].iloc[0], errors='coerce')
        
        df_collections = load_historical_sheet("3. All Countries Mar-25 - IBSAR - Collection Accounts.xlsx", sheet_name="13011", header_keyword="Row Labels")
        target_collections = pd.to_numeric(df_collections[df_collections['Row Labels'] == COUNTRY_CODE]['Grand Total'].iloc[0], errors='coerce')
        
        df_other_ar = load_historical_sheet("4. All Countries Mar-25 - IBSAR Other AR related Accounts.xlsx", sheet_name="18350", header_keyword="COUNTRY")
        target_other_ar = pd.to_numeric(df_other_ar[df_other_ar['COUNTRY'].str.strip().str.lower() == COUNTRY_NAME.lower()]['Remaining Amount'], errors='coerce').sum()
        
        targets_total = target_customers + target_collections + target_other_ar
        print(f"   - Total 'Targets': {targets_total:,.2f}")

        variance = actuals_total - targets_total
        print(f"➡️   Calculated Variance: {variance:,.2f}")
        status = "RECONCILED" if abs(variance) < 1000 else "VARIANCE DETECTED"
        print(f"✅ Reconciliation Status: {status}")
    except (FileNotFoundError, IndexError, KeyError, ValueError) as e:
        print(f"❌ ERROR during reconciliation: {e}."); import traceback; traceback.print_exc(); sys.exit(1)

    # --- PHASE 3: BRIDGES & ADJUSTMENTS ANALYSIS ---
    print("\n--- Phase 3: Classifying Variances (Bridges & Adjustments) ---")
    print("   - Loading detailed transactional data for analysis...")
    df_for_classification = load_historical_sheet("1. All Countries Mar-25 - IBSAR - Consolidation.xlsx", sheet_name="Consolidated data", header_keyword="GL Account")
    
    df_normalized = normalize_for_bridges(df_for_classification)
    
    print("   - Applying classification agent...")
    bridge_rules = load_rules()
    df_classified = classify_bridges(df_normalized, bridge_rules)
    classified_count = df_classified['bridge_key'].notna().sum()
    print(f"   - Classification complete. {classified_count} of {len(df_classified)} transactions were classified.")

    # --- PHASE 4: FINAL REPORT GENERATION ---
    print("\n--- Phase 4: Generating Final Reports ---")
    summary_report_path = os.path.join(OUTPUT_PATH, "demo_summary_report.txt")
    with open(summary_report_path, "w") as f:
        f.write(f"--- SOXauto DEMONSTRATION REPORT FOR {COUNTRY_NAME} ---\n")
        f.write(f"Execution Date: {datetime.now().isoformat()}\n\n")
        f.write("--- RECONCILIATION SUMMARY ---\n")
        f.write(f"Total Actuals (GL): {actuals_total:,.2f}\n")
        f.write(f"Total Targets (IPEs): {targets_total:,.2f}\n")
        f.write(f"Variance: {variance:,.2f}\n")
        f.write(f"Status: {status}\n\n")
        f.write("--- VARIANCE CLASSIFICATION OVERVIEW ---\n")
        f.write("Distribution of 'Bridges' on consolidated data:\n")
        classification_summary = df_classified['bridge_key'].value_counts(dropna=False).to_string()
        f.write(classification_summary)

    print(f"✅ Summary report generated: {summary_report_path}")
    print("\n🎉 Full pipeline demonstration completed successfully! 🎉")

if __name__ == "__main__":
    main()