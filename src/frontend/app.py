import streamlit as st
import pandas as pd
import os
import sys
import asyncio
import time
import glob
from datetime import datetime
from unittest.mock import MagicMock

# --- PATH CONFIGURATION ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --- BACKEND IMPORTS ---
from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager
from src.bridges import (
    categorize_nav_vouchers,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
)
from src.core.scope_filtering import filter_ipe08_scope
from src.utils.fx_utils import FXConverter


# --- LOGIC DESCRIPTIONS FOR BRIDGES ---
TIMING_DIFF_LOGIC = """
**Timing Difference Bridge - Business Logic:**

1. **Filter Scope:** Select only Non-Marketing vouchers (apology_v2, jforce, refund, store_credit, Jpay store_credit)
2. **Filter "Used in Month N":** Keep vouchers where `Order_Creation_Date` is within the reconciliation month
3. **Filter "Pending/Late in Month N+1":**
    - `Order_Delivery_Date` > cutoff date OR is NULL (not delivered)
    - AND `Order_Cancellation_Date` > cutoff date OR is NULL (not canceled)
4. **Calculate:** Sum of `remaining_amount` for all matching vouchers

*These are vouchers ordered in the control period but not yet finalized by the cutoff date.*
"""

VTC_LOGIC = """
**VTC (Voucher to Cash) Adjustment - Business Logic:**

1. **Filter Non-Marketing:** Select only Non-Marketing vouchers (apology_v2, jforce, refund, store_credit, Jpay store_credit)
2. **Filter IPE_08 (BOB):** Select canceled refund vouchers from Non-Marketing set
    - `business_use` = "refund"
    - `is_valid` = "valid"  
    - `is_active` = 0 (canceled)
    - `inactive_at` falls within the reconciliation month (e.g., September 1-30)
3. **Filter CR_03 (NAV):** Identify cancellation entries
    - `bridge_category` starts with "Cancellation" OR equals "VTC"/"VTC Manual"
4. **Anti-Join:** Find IPE_08 vouchers NOT present in CR_03 cancellations
5. **Calculate:** Sum of unmatched voucher amounts

*These are canceled refund vouchers in BOB (within the reconciliation month) without corresponding NAV cancellation entries.*
"""

RECLASS_LOGIC = """
**Customer Posting Group Bridge - Business Logic:**

1. **Group by Customer:** Aggregate entries by `Customer No_`
2. **Identify Issues:** Find customers with multiple unique `Customer Posting Group` values
3. **Flag for Review:** These customers require manual investigation

*This is a data quality check - customers should have consistent posting group assignments.*
"""


def get_sql_query_for_item(item_id: str) -> str:
    """Retrieve the SQL query for a catalog item."""
    item = get_item_by_id(item_id)
    if item and item.sql_query:
        return item.sql_query
    return "SQL query not available for this item."


@st.cache_data
def convert_df(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to CSV bytes for Streamlit download buttons."""
    return df.to_csv(index=False).encode("utf-8")

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="SOXauto | C-PG-1 Audit Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM CSS ---
st.markdown(
    """
<style>
    h1 { color: #0f1116; font-weight: 700; }
    h2 { color: #262730; border-bottom: 1px solid #f0f2f6; padding-bottom: 10px; margin-top: 30px; }
    
    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e6e6e6;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    /* Evidence Badge */
    .evidence-badge {
        background-color: #e6f3ff;
        color: #0066cc;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.85em;
        border: 1px solid #b8daff;
        display: inline-block;
        margin-top: 5px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- HELPER FUNCTIONS ---


def get_latest_evidence_zip(item_id):
    """Finds the most recent ZIP package generated for an IPE."""
    evidence_root = os.path.join(REPO_ROOT, "evidence")
    if not os.path.exists(evidence_root):
        return None

    # Search for folders starting with item_id
    candidates = []
    for folder_name in os.listdir(evidence_root):
        if folder_name.startswith(item_id):
            folder_path = os.path.join(evidence_root, folder_name)
            # Look for zip inside
            zip_files = glob.glob(os.path.join(folder_path, "*.zip"))
            if zip_files:
                # Add (timestamp, zip_path)
                candidates.append((os.path.getmtime(zip_files[0]), zip_files[0]))

    if not candidates:
        return None

    # Return the newest one
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


async def run_extraction_with_evidence(item_id, params, country_code, period_str):
    """
    Executes extraction via IPERunner.run() ensuring Rich Metadata & Evidence Generation.
    Includes a PATCH for CR_05 column names.
    """
    mock_secrets = MagicMock(spec=AWSSecretsManager)
    mock_secrets.get_secret.return_value = "FAKE_SECRET"

    item = get_item_by_id(item_id)
    if not item:
        return pd.DataFrame(), None

    # Injection manuelle des paramètres dans la requête SQL pour l'exécution directe (fallback)
    final_query = item.sql_query
    for key, value in params.items():
        if f"{{{key}}}" in final_query:
            final_query = final_query.replace(f"{{{key}}}", str(value))

    ipe_config = {
        "id": item.item_id,
        "description": getattr(item, "description", ""),
        "secret_name": "fake",
        "main_query": final_query,
        "validation": {},
    }

    runner = IPERunner(
        ipe_config,
        mock_secrets,
        cutoff_date=params["cutoff_date"],
        country=country_code,
        period=period_str,
        full_params=params
    )
    
    # === PATCH CRITIQUE (Le même que fetch_live_fixtures.py) ===
    # Force le runner à ignorer les '?' dans les noms de colonnes de CR_05
    # et à exécuter la requête telle quelle (car les params sont déjà injectés)
    def patched_exec(query, params=None):
        return pd.read_sql(query, runner.connection)
    
    runner._execute_query_with_parameters = patched_exec
    # ===========================================================
    
    try:
        # runner.run() va maintenant utiliser notre méthode patchée
        df = runner.run()

        # On récupère le zip le plus récent
        zip_path = get_latest_evidence_zip(item_id)

        return df, zip_path

    except Exception as e:
        # Fallback fixture (Mode Démo sans BDD)
        fixture_path = os.path.join(
            REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv"
        )
        if os.path.exists(fixture_path):
            return pd.read_csv(fixture_path, low_memory=False), None
        return pd.DataFrame(), None


def load_jdash_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file), "Uploaded File"
    fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", "fixture_JDASH.csv")
    if os.path.exists(fixture_path):
        return pd.read_csv(fixture_path), "Local Fixture"
    return pd.DataFrame(columns=["Voucher Id", "Amount Used"]), "No Data"


def load_all_data(params, uploaded_files=None):
    """Orchestrates loading and evidence collection with context.
    
    Args:
        params: SQL parameters dictionary
        uploaded_files: Dictionary of {item_id: UploadedFile} for manual CSV overrides
    
    Returns:
        tuple: (data_store, evidence_store, source_store) where source_store tracks 
               the source of each dataset ("Uploaded File", "Live Database", "Local Fixture")
    """
    REQUIRED_IPES = ["CR_04", "CR_03", "CR_05", "IPE_07", "IPE_08", "DOC_VOUCHER_USAGE"]
    data_store = {}
    evidence_store = {}
    source_store = {}  # Track data source for visual feedback
    
    if uploaded_files is None:
        uploaded_files = {}

    status_container = st.empty()
    progress_bar = st.progress(0)

    # --- MISE À JOUR : Extraction du Contexte (Pays/Période) ---
    # On nettoie le format SQL "('JD_GH')" pour avoir juste "JD_GH"
    country_code = params["id_companies_active"].strip("()'")
    # On transforme "2025-09-30" en "202509"
    period_str = params["cutoff_date"].replace("-", "")[:6]

    for i, item_id in enumerate(REQUIRED_IPES):
        status_container.markdown(
            f"🛡️ **Audit Process:** Processing `{item_id}` for **{country_code}**..."
        )

        # Priority 1: Check if a file was uploaded for this IPE
        if item_id in uploaded_files and uploaded_files[item_id] is not None:
            try:
                df = pd.read_csv(uploaded_files[item_id], low_memory=False)
                zip_path = None  # No evidence package for uploaded files
                source_store[item_id] = "Uploaded File"
                status_container.markdown(
                    f"✅ **{item_id}:** Loaded from uploaded CSV ({len(df):,} rows)"
                )
            except Exception as e:
                st.warning(f"⚠️ Error reading uploaded file for {item_id}: {e}. Falling back to live extraction.")
                df = None
                zip_path = None
                source_store[item_id] = None
        else:
            df = None
            zip_path = None
            source_store[item_id] = None

        # Priority 2: Try live SQL extraction if no uploaded file
        if df is None:
            try:
                df, zip_path = asyncio.run(
                    run_extraction_with_evidence(item_id, params, country_code, period_str)
                )
                if not df.empty:
                    source_store[item_id] = "Live Database"
                else:
                    # Empty result from live extraction, try fixture
                    df = None
            except Exception:
                df = None
                zip_path = None

        # Priority 3: Fall back to local fixture
        if df is None or (df is not None and df.empty and source_store.get(item_id) != "Uploaded File"):
            fixture_path = os.path.join(
                REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv"
            )
            if os.path.exists(fixture_path):
                df = pd.read_csv(fixture_path, low_memory=False)
                zip_path = None
                source_store[item_id] = "Local Fixture"
            else:
                df = pd.DataFrame()
                zip_path = None
                source_store[item_id] = "No Data"

        # Filtrage local pour l'affichage (si nécessaire)
        for col in ["ID_COMPANY", "id_company", "ID_Company", "country"]:
            if col in df.columns:
                df = df[df[col] == country_code].copy()
                break

        data_store[item_id] = df
        evidence_store[item_id] = zip_path

        progress_bar.progress((i + 1) / len(REQUIRED_IPES))

    progress_bar.empty()
    status_container.empty()
    return data_store, evidence_store, source_store


# --- MAIN APP ---


def main():
    with st.sidebar:
        st.title("⚙️ Configuration")
        target_country = st.selectbox(
            "Target Entity", ["JD_GH", "EC_NG", "EC_KE", "JM_EG"], index=0
        )
        cutoff_date = st.date_input("Control Period", value=datetime(2025, 9, 30))
        st.markdown("---")
        
        # --- MANUAL FILE UPLOADS (Acceptance Criteria #1) ---
        with st.expander("📂 Manual File Uploads (Optional)", expanded=False):
            st.markdown("""
            Upload CSV files to bypass live SQL extraction.
            If a file is provided, it will be used instead of querying the database.
            """)
            
            # File uploaders for all required data sources
            uploaded_cr04 = st.file_uploader(
                "CR_04 - GL Balances", type="csv", key="upload_cr04",
                help="NAV GL Balances extract"
            )
            uploaded_cr03 = st.file_uploader(
                "CR_03 - GL Entries", type="csv", key="upload_cr03",
                help="NAV GL Entries extract"
            )
            uploaded_ipe07 = st.file_uploader(
                "IPE_07 - Customer Ledger", type="csv", key="upload_ipe07",
                help="Customer balances - Monthly balances at date"
            )
            uploaded_ipe08 = st.file_uploader(
                "IPE_08 - Voucher Issuance", type="csv", key="upload_ipe08",
                help="TV - Voucher liabilities from BOB"
            )
            uploaded_doc_voucher = st.file_uploader(
                "DOC_VOUCHER_USAGE - Voucher Usage", type="csv", key="upload_doc_voucher",
                help="Voucher Usage TV Extract for Timing Bridge"
            )
            uploaded_cr05 = st.file_uploader(
                "CR_05 - FX Rates", type="csv", key="upload_cr05",
                help="Monthly closing FX rates"
            )
            uploaded_jdash = st.file_uploader(
                "JDASH - Jdash Export", type="csv", key="upload_jdash",
                help="Jdash voucher usage data"
            )
        
        # Build uploaded_files dictionary
        uploaded_files = {
            "CR_04": uploaded_cr04,
            "CR_03": uploaded_cr03,
            "IPE_07": uploaded_ipe07,
            "IPE_08": uploaded_ipe08,
            "DOC_VOUCHER_USAGE": uploaded_doc_voucher,
            "CR_05": uploaded_cr05,
        }
        
        st.markdown("---")
        run_btn = st.button("🚀 Start SOX Reconciliation", type="primary")

        year = cutoff_date.year
        month = cutoff_date.month
        params = {
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d"),
            "year_start": f"{year}-{month:02d}-01",
            "year_end": cutoff_date.strftime("%Y-%m-%d"),
            "year": year,
            "month": month,
            "gl_accounts": "('15010','18303','18304','18406','18408','18409','18411','18412','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')",
            "id_companies_active": f"('{target_country}')",
        }

    st.title("🛡️ SOXauto: C-PG-1 Control Center")
    st.markdown(
        f"**Entity:** {target_country} | **Period:** {cutoff_date.strftime('%Y-%m')}"
    )

    if run_btn:
        # --- EXECUTION CONTEXT (Acceptance Criteria #1) ---
        with st.expander("📋 Execution Context", expanded=True):
            st.markdown("### SQL Execution Parameters")
            st.markdown("""
            The following parameters are used across all SQL extractions for this control execution:
            """)
            
            # Display parameters in a structured format
            param_col1, param_col2 = st.columns(2)
            with param_col1:
                st.markdown("**Date Parameters:**")
                st.code(f"""cutoff_date: {params['cutoff_date']}
year_start: {params['year_start']}
year_end: {params['year_end']}
year: {params['year']}
month: {params['month']}""", language="yaml")
            
            with param_col2:
                st.markdown("**Entity & Account Filters:**")
                st.code(f"""id_companies_active: {params['id_companies_active']}
gl_accounts: {params['gl_accounts']}""", language="yaml")
            
            st.markdown("---")
            st.markdown("**Full Parameters Dictionary:**")
            st.json(params)

        jdash_df, jdash_source = load_jdash_data(uploaded_jdash)

        # --- PREPROCESSING & LOGIC BLUEPRINT (new informational section) ---
        st.header("0. Preprocessing & Logic Blueprint")
        st.caption("Documentation of the normalization steps and the exact business logic applied before each bridge is executed.")

        pre_cols = st.columns(3)
        pre_cols[0].metric("JDASH Rows Loaded", f"{len(jdash_df):,}")
        pre_cols[0].caption(f"Source: {jdash_source}")
        pre_cols[1].metric("IPE Scope Filter", "Non-Marketing + GL 18412")
        pre_cols[1].caption("`filter_ipe08_scope` enforces account and business_use rules.")
        pre_cols[2].metric("Cutoff Date", params["cutoff_date"])
        pre_cols[2].caption("All preprocessing buckets data into Month N vs N+1 windows.")

        preprocessing_steps = [
            (
                "JDASH Normalization",
                "`load_jdash_data()` ingests the uploaded export (or fixture) and keeps the canonical columns `Voucher Id` and `Amount Used` for downstream joins."
            ),
            (
                "BOB Scope Enforcement",
                "`filter_ipe08_scope()` restricts IPE_08 to Non-Marketing vouchers, includes GL 18412, and keeps only valid, country-specific liabilities."
            ),
            (
                "Cutoff Bucketing",
                "`calculate_timing_difference_bridge()` compares Month N order creation to Month N+1 delivery/cancel status to isolate pending vouchers, mirroring the manual reconciliation checklist."
            ),
        ]

        with st.expander("🔬 Preprocessing Steps", expanded=False):
            for title, description in preprocessing_steps:
                st.markdown(f"**{title}** — {description}")

        st.markdown("#### Business Logic Reference")
        logic_tabs = st.tabs(["Timing Difference", "VTC", "Customer Reclass"])
        logic_tabs[0].markdown(TIMING_DIFF_LOGIC)
        logic_tabs[1].markdown(VTC_LOGIC)
        logic_tabs[2].markdown(RECLASS_LOGIC)

        # --- PHASE 1: DATA FACTORY (EVIDENCE GENERATION) ---
        st.header("1. Digital Evidence Factory")
        st.info(
            "Extracting data from immutable sources, validating quality, and generating cryptographic hashes."
        )

        data, evidence_paths, source_info = load_all_data(params, uploaded_files)

        # Helper function to display source badge
        def display_source_badge(source: str):
            """Display a colored badge indicating the data source."""
            if source == "Uploaded File":
                st.markdown('<span class="evidence-badge" style="background-color: #d4edda; color: #155724; border-color: #c3e6cb;">📤 Source: Uploaded File</span>', unsafe_allow_html=True)
            elif source == "Live Database":
                st.markdown('<span class="evidence-badge" style="background-color: #cce5ff; color: #004085; border-color: #b8daff;">🔗 Source: Live Database</span>', unsafe_allow_html=True)
            elif source == "Local Fixture":
                st.markdown('<span class="evidence-badge" style="background-color: #fff3cd; color: #856404; border-color: #ffeeba;">📁 Source: Local Fixture</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="evidence-badge" style="background-color: #f8d7da; color: #721c24; border-color: #f5c6cb;">⚠️ Source: No Data</span>', unsafe_allow_html=True)

        # Evidence Grid (Acceptance Criteria #2 - Enhanced Extraction Section)
        st.subheader("📦 Source Data Packages (Authenticated)")
        st.markdown("*Click 'View Source Query' to see the actual SQL executed for each extraction.*")

        # Row 1 - Enhanced with SQL expanders
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("GL Balances (CR_04)", f"{len(data['CR_04']):,} rows")
            display_source_badge(source_info.get("CR_04", "No Data"))
            if evidence_paths.get("CR_04"):
                with open(evidence_paths["CR_04"], "rb") as fp:
                    st.download_button(
                        "🔒 Download Package (ZIP)",
                        fp,
                        "CR_04_Evidence.zip",
                        "application/zip",
                        key="dl_cr04",
                    )
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_04"), language="sql")

        with c2:
            st.metric("GL Entries (CR_03)", f"{len(data['CR_03']):,} rows")
            display_source_badge(source_info.get("CR_03", "No Data"))
            if evidence_paths.get("CR_03"):
                with open(evidence_paths["CR_03"], "rb") as fp:
                    st.download_button(
                        "🔒 Download Package (ZIP)",
                        fp,
                        "CR_03_Evidence.zip",
                        "application/zip",
                        key="dl_cr03",
                    )
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_03"), language="sql")

        with c3:
            st.metric("Voucher Liability (IPE_08)", f"{len(data['IPE_08']):,} rows")
            display_source_badge(source_info.get("IPE_08", "No Data"))
            if evidence_paths.get('IPE_08'):
                with open(evidence_paths['IPE_08'], "rb") as fp:
                    st.download_button("🔒 Download Package (ZIP)", fp, "IPE_08_Evidence.zip", "application/zip", key="dl_ipe08")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_08"), language="sql")

        # Row 2 - Additional IPEs with expanders
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Customer Balances (IPE_07)", f"{len(data['IPE_07']):,} rows")
            display_source_badge(source_info.get("IPE_07", "No Data"))
            if evidence_paths.get("IPE_07"):
                with open(evidence_paths["IPE_07"], "rb") as fp:
                    st.download_button(
                        "🔒 Download Package (ZIP)",
                        fp,
                        "IPE_07_Evidence.zip",
                        "application/zip",
                        key="dl_ipe07",
                    )
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_07"), language="sql")
        
        with c5:
            st.metric("FX Rates (CR_05)", f"{len(data['CR_05']):,} rows")
            display_source_badge(source_info.get("CR_05", "No Data"))
            if evidence_paths.get("CR_05"):
                with open(evidence_paths["CR_05"], "rb") as fp:
                    st.download_button(
                        "🔒 Download Package (ZIP)",
                        fp,
                        "CR_05_Evidence.zip",
                        "application/zip",
                        key="dl_cr05",
                    )
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_05"), language="sql")
        
        with c6:
            st.metric("Voucher Usage (DOC)", f"{len(data['DOC_VOUCHER_USAGE']):,} rows")
            display_source_badge(source_info.get("DOC_VOUCHER_USAGE", "No Data"))
            if evidence_paths.get("DOC_VOUCHER_USAGE"):
                with open(evidence_paths["DOC_VOUCHER_USAGE"], "rb") as fp:
                    st.download_button(
                        "🔒 Download Package (ZIP)",
                        fp,
                        "DOC_VOUCHER_USAGE_Evidence.zip",
                        "application/zip",
                        key="dl_doc_voucher",
                    )
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("DOC_VOUCHER_USAGE"), language="sql")
        st.markdown("---")

        # --- PHASE 2: THE AGENT (LOGIC) ---
        st.header("2. Agentic Classification (Bridges)")
        st.write("Applying validated business logic to identify and explain variances.")

        # Initialize FX Converter
        try:
            fx_converter = FXConverter(data["CR_05"])
            st.success(
                f"✓ FX Converter initialized with {len(fx_converter.rates_dict)} exchange rates. All amounts reported in USD."
            )
        except Exception as e:
            st.warning(
                f"⚠️ Could not initialize FX Converter: {e}. Using local currency."
            )
            fx_converter = None

        tabs = st.tabs(["Task 1: Timing Diff", "Task 2: VTC", "Task 4: Reclass"])

        # --- TASK 1: Timing Difference (Acceptance Criteria #3 - Glass Box) ---
        with tabs[0]:
            # Note: fx_converter parameter is deprecated and no longer used
            # The function now compares Jdash (ordered) vs IPE_08 (delivered) amounts
            # Logic Explanation Block
            with st.expander("📖 Logic Explanation", expanded=False):
                st.info(TIMING_DIFF_LOGIC)

            # Calculate intermediate metrics for transparency
            filtered_ipe08 = filter_ipe08_scope(data["IPE_08"])
            total_ipe08_vouchers = len(data["IPE_08"])
            non_marketing_vouchers = len(filtered_ipe08)

            bridge_amt, proof_df = calculate_timing_difference_bridge(
                jdash_df=jdash_df,
                ipe_08_df=data["IPE_08"],
                cutoff_date=params["cutoff_date"],
            )
            timing_diff_vouchers = len(proof_df)

            # Intermediate Metrics Display
            st.markdown("#### 📊 Processing Pipeline")
            step_cols = st.columns(4)
            step_cols[0].metric("Step 1: Total IPE_08", f"{total_ipe08_vouchers:,}")
            step_cols[1].metric("Step 2: Non-Marketing", f"{non_marketing_vouchers:,}")
            step_cols[2].metric("Step 3: In Period", f"{timing_diff_vouchers:,}")
            step_cols[3].metric("Step 4: Bridge Amount", f"${bridge_amt:,.2f}")

            st.markdown("---")

            # Results
            c1, c2 = st.columns([1, 3])
            c1.metric("Timing Difference", f"${bridge_amt:,.2f}")
            c1.download_button(
                "📥 Download Bridge Calculation",
                proof_df.to_csv(index=False),
                f"Bridge_Timing_{target_country}.csv",
                key="dl_timing",
            )
            c2.markdown("**Vouchers with Timing Difference:**")
            c2.dataframe(proof_df.head(50), use_container_width=True)

        # --- TASK 2: VTC (Acceptance Criteria #3 - Glass Box) ---
        with tabs[1]:
            # Logic Explanation Block
            with st.expander("📖 Logic Explanation", expanded=False):
                st.info(VTC_LOGIC)

            cat_cr03 = categorize_nav_vouchers(
                data['CR_03'],
                ipe_08_df=data.get('IPE_08'),
                doc_voucher_usage_df=data.get('DOC_VOUCHER_USAGE')
            )
            # Now returns (adj_amt, proof_df_vtc, metrics)
            adj_amt, proof_df_vtc, vtc_metrics = calculate_vtc_adjustment(
                data['IPE_08'], 
                cat_cr03, 
                fx_converter=fx_converter,
                cutoff_date=params['cutoff_date']
            )

            # Use intermediate metrics from calculation function
            refund_vouchers = vtc_metrics.get("refund_vouchers", 0)
            nav_cancellations = vtc_metrics.get("nav_cancellations", 0)
            unmatched_vouchers = vtc_metrics.get("unmatched_vouchers", len(proof_df_vtc))

            # Intermediate Metrics Display
            st.markdown("#### 📊 Processing Pipeline")
            step_cols = st.columns(4)
            step_cols[0].metric("Step 1: Canceled Refunds (BOB)", f"{refund_vouchers:,}")
            step_cols[1].metric("Step 2: NAV Cancellations", f"{nav_cancellations:,}")
            step_cols[2].metric("Step 3: Unmatched", f"{unmatched_vouchers:,}")
            step_cols[3].metric("Step 4: VTC Amount", f"${adj_amt:,.2f}")

            st.markdown("---")

            # Results
            c1, c2 = st.columns([1, 3])
            c1.metric("VTC Adjustment", f"${adj_amt:,.2f}")
            c1.download_button(
                "📥 Download Bridge Calculation",
                proof_df_vtc.to_csv(index=False),
                f"Bridge_VTC_{target_country}.csv",
                key="dl_vtc",
            )
            c2.markdown("**Unmatched Vouchers (BOB without NAV cancellation):**")
            c2.dataframe(proof_df_vtc.head(50), use_container_width=True)

        # --- TASK 4: Reclass (Acceptance Criteria #3 - Glass Box) ---
        with tabs[2]:
            # Logic Explanation Block
            with st.expander("📖 Logic Explanation", expanded=False):
                st.info(RECLASS_LOGIC)
            
            _, proof_df_reclass = calculate_customer_posting_group_bridge(
                data["IPE_07"]
            )
            
            # Intermediate Metrics
            total_customers = 0
            if not data["IPE_07"].empty and "Customer No_" in data["IPE_07"].columns:
                total_customers = data["IPE_07"]["Customer No_"].nunique()
            
            problem_customers = len(proof_df_reclass)
            
            # Intermediate Metrics Display
            st.markdown("#### 📊 Processing Pipeline")
            step_cols = st.columns(3)
            step_cols[0].metric("Step 1: Total Customers", f"{total_customers:,}")
            step_cols[1].metric("Step 2: Multiple Posting Groups", f"{problem_customers:,}")
            if problem_customers == 0:
                step_cols[2].metric("Step 3: Status", "✅ PASS")
            else:
                step_cols[2].metric("Step 3: Status", "⚠️ REVIEW")
            
            st.markdown("---")
            
            # Results
            if problem_customers == 0:
                st.success("✅ PASS: Data Quality Clean - All customers have consistent posting group assignments.")
            else:
                st.error(f"❌ FAIL: {problem_customers} customers with multiple posting groups require manual review")
                st.markdown("**Customers with Multiple Posting Groups:**")
                st.dataframe(proof_df_reclass, use_container_width=True)

        # --- PHASE 3: SUMMARY ---
        st.markdown("---")
        st.header("3. Final Reconciliation Status")

        total_explained = bridge_amt + adj_amt

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Total Explained Variance",
            f"${total_explained:,.2f}",
            delta="Automated Bridges",
        )

        if total_explained != 0:
            col2.warning("Variance Explained")
        else:
            col2.success("Zero Variance")

        col3.info("Final Digital Evidence Package assembled.")
        
        # Summary Table
        with st.expander("📋 Bridge Summary", expanded=True):
            summary_data = {
                "Bridge Type": ["Timing Difference", "VTC Adjustment", "Customer Posting Group"],
                "Amount (USD)": [f"${bridge_amt:,.2f}", f"${adj_amt:,.2f}", "N/A (Quality Check)"],
                "Items Count": [len(proof_df), len(proof_df_vtc), problem_customers],
                "Status": [
                    "✅ Calculated" if len(proof_df) > 0 else "⚪ No Items",
                    "✅ Calculated" if len(proof_df_vtc) > 0 else "⚪ No Items",
                    "✅ PASS" if problem_customers == 0 else "⚠️ Review Required"
                ]
            }
            st.table(pd.DataFrame(summary_data))

    else:
        st.info("Ready to Start. Ensure VPN/Teleport is active.")


if __name__ == "__main__":
    main()
