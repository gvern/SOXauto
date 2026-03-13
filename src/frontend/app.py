import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# --- PATH CONFIGURATION ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --- BACKEND IMPORTS ---
from src.core.catalog.cpg1 import get_item_by_id
from src.core.extraction_pipeline import load_all_data as load_all_data_pipeline
from src.core.jdash_loader import load_jdash_data as load_jdash_data_pipeline
from src.core.reconciliation.voucher_classification import categorize_vouchers
from src.bridges import (
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
)
from src.core.scope_filtering import filter_ipe08_scope
from src.utils.fx_utils import FXConverter
from src.utils.date_utils import format_yyyy_mm_dd
from src.utils.query_params_builder import build_complete_query_params


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
    if item_id == "DOC_VOUCHER_USAGE":
        item_id = "IPE_08_USAGE"

    item = get_item_by_id(item_id)
    if item and item.sql_query:
        return item.sql_query
    return "SQL query not available for this item."


@st.cache_data
def convert_df(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to CSV bytes for Streamlit download buttons."""
    return df.to_csv(index=False).encode("utf-8")


def load_jdash_data(uploaded_file, company: str | None = None):
    """Load JDASH data via core loader (uploaded file preferred, then fixtures)."""
    return load_jdash_data_pipeline(
        source=uploaded_file,
        fixture_fallback=True,
        company=company,
    )


def load_all_data(params, uploaded_files=None):
    """Load required datasets via core extraction pipeline."""
    return load_all_data_pipeline(
        params=params,
        uploaded_files=uploaded_files,
    )

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

# --- MAIN APP ---


def main():
    if "run_reconciliation_started" not in st.session_state:
        st.session_state["run_reconciliation_started"] = False

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
                "IPE_08_ISSUANCE - Voucher Issuance", type="csv", key="upload_ipe08",
                help="TV voucher issuance extract (liability baseline)"
            )
            uploaded_ipe08_timing = st.file_uploader(
                "IPE_08_TIMING - Timing Extract", type="csv", key="upload_ipe08_timing",
                help="Inactive vouchers still valid at cutoff (timing support)"
            )
            uploaded_doc_voucher = st.file_uploader(
                "IPE_08_USAGE - Voucher Usage", type="csv", key="upload_doc_voucher",
                help="Voucher Usage TV Extract for Timing Bridge"
            )
            uploaded_cr05 = st.file_uploader(
                "CR_05 - FX Rates", type="csv", key="upload_cr05",
                help="Monthly closing FX rates"
            )
            uploaded_ipe10 = st.file_uploader(
                "IPE_10 - Customer Prepayments", type="csv", key="upload_ipe10",
                help="Customer prepayments liability extract"
            )
            uploaded_ipe12 = st.file_uploader(
                "IPE_12 - Delivered Not Reconciled", type="csv", key="upload_ipe12",
                help="Delivered packages not yet reconciled"
            )
            uploaded_ipe31 = st.file_uploader(
                "IPE_31 - Collection Accounts", type="csv", key="upload_ipe31",
                help="Payment Gateway detailed TV extraction"
            )
            uploaded_ipe34 = st.file_uploader(
                "IPE_34 - Marketplace Refund Liability", type="csv", key="upload_ipe34",
                help="Marketplace refund liabilities extract"
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
            "IPE_08_ISSUANCE": uploaded_ipe08,
            "IPE_08_TIMING": uploaded_ipe08_timing,
            "DOC_VOUCHER_USAGE": uploaded_doc_voucher,
            "IPE_08_USAGE": uploaded_doc_voucher,
            "CR_05": uploaded_cr05,
            "IPE_10": uploaded_ipe10,
            "IPE_12": uploaded_ipe12,
            "IPE_31": uploaded_ipe31,
            "IPE_34": uploaded_ipe34,
        }
        
        st.markdown("---")
        run_btn = st.button("🚀 Start SOX Reconciliation", type="primary")
        if run_btn:
            st.session_state["run_reconciliation_started"] = True

        params = build_complete_query_params(
            cutoff_date=format_yyyy_mm_dd(cutoff_date),
            countries=[target_country],
            period=cutoff_date.strftime("%Y-%m"),
            overrides={"company": target_country},
        )

    st.title("🛡️ SOXauto: C-PG-1 Control Center")
    st.markdown(
        f"**Entity:** {target_country} | **Period:** {cutoff_date.strftime('%Y-%m')}"
    )

    if st.session_state["run_reconciliation_started"]:
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

        jdash_df, jdash_source = load_jdash_data(uploaded_jdash, target_country)

        # --- PREPROCESSING & LOGIC BLUEPRINT (new informational section) ---
        st.header("0. Preprocessing & Logic Blueprint")
        st.caption("Documentation of the normalization steps and the exact business logic applied before each bridge is executed.")

        pre_cols = st.columns(3)
        pre_cols[0].metric("JDASH Rows Loaded", f"{len(jdash_df):,}")
        pre_cols[0].caption(f"Source: {jdash_source}")
        pre_cols[1].metric("IPE_08_ISSUANCE Scope", "Non-Marketing + GL 18412")
        pre_cols[1].caption("`filter_ipe08_scope` enforces account and business_use rules on issuance data.")
        pre_cols[2].metric("Cutoff Date", params["cutoff_date"])
        pre_cols[2].caption("All preprocessing buckets data into Month N vs N+1 windows.")

        preprocessing_steps = [
            (
                "JDASH Normalization",
                "`load_jdash_data()` ingests the uploaded export (or fixture) and keeps the canonical columns `Voucher Id` and `Amount Used` for downstream joins."
            ),
            (
                "BOB Scope Enforcement",
                "`filter_ipe08_scope()` restricts IPE_08_ISSUANCE (legacy: IPE_08) to Non-Marketing vouchers, includes GL 18412, and keeps only valid, country-specific liabilities."
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

        def render_download_controls(
            item_id: str,
            df: pd.DataFrame,
            evidence_path: str | None,
            zip_filename: str,
            key_prefix: str,
        ):
            """Render reliable ZIP/CSV download actions for one data package."""
            if evidence_path and os.path.exists(evidence_path):
                with open(evidence_path, "rb") as fp:
                    st.download_button(
                        "🔒 Download Evidence (ZIP)",
                        fp.read(),
                        zip_filename,
                        "application/zip",
                        key=f"{key_prefix}_zip",
                    )
            else:
                st.caption("No evidence ZIP available for this source.")

            if df is not None and not df.empty:
                st.download_button(
                    "📄 Download Data (CSV)",
                    convert_df(df),
                    f"{item_id}.csv",
                    "text/csv",
                    key=f"{key_prefix}_csv",
                )

        # Evidence Grid (Acceptance Criteria #2 - Enhanced Extraction Section)
        st.subheader("📦 Source Data Packages (Authenticated)")
        st.markdown("*Click 'View Source Query' to see the actual SQL executed for each extraction.*")

        st.markdown("**Core CR Extracts**")

        # Row 1 - Core CR extracts
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("GL Balances (CR_04)", f"{len(data['CR_04']):,} rows")
            display_source_badge(source_info.get("CR_04", "No Data"))
            cr04_evidence_path = evidence_paths.get("CR_04")
            render_download_controls("CR_04", data["CR_04"], cr04_evidence_path, "CR_04_Evidence.zip", "dl_cr04")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_04"), language="sql")

        with c2:
            st.metric("GL Entries (CR_03)", f"{len(data['CR_03']):,} rows")
            display_source_badge(source_info.get("CR_03", "No Data"))
            cr03_evidence_path = evidence_paths.get("CR_03")
            render_download_controls("CR_03", data["CR_03"], cr03_evidence_path, "CR_03_Evidence.zip", "dl_cr03")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_03"), language="sql")

        with c3:
            st.metric("FX Rates (CR_05)", f"{len(data['CR_05']):,} rows")
            display_source_badge(source_info.get("CR_05", "No Data"))
            cr05_evidence_path = evidence_paths.get("CR_05")
            render_download_controls("CR_05", data["CR_05"], cr05_evidence_path, "CR_05_Evidence.zip", "dl_cr05")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("CR_05"), language="sql")

        st.markdown("**Voucher Package (IPE_08 Split)**")

        # Row 2 - IPE_08 split extracts
        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Customer Balances (IPE_07)", f"{len(data['IPE_07']):,} rows")
            display_source_badge(source_info.get("IPE_07", "No Data"))
            ipe07_evidence_path = evidence_paths.get("IPE_07")
            render_download_controls("IPE_07", data["IPE_07"], ipe07_evidence_path, "IPE_07_Evidence.zip", "dl_ipe07")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_07"), language="sql")
        
        with c5:
            st.metric("Voucher Issuance (IPE_08_ISSUANCE)", f"{len(data.get('IPE_08_ISSUANCE', data.get('IPE_08', pd.DataFrame()))):,} rows")
            display_source_badge(source_info.get("IPE_08_ISSUANCE", source_info.get("IPE_08", "No Data")))
            issuance_df = data.get('IPE_08_ISSUANCE', data.get('IPE_08', pd.DataFrame()))
            issuance_evidence_path = evidence_paths.get('IPE_08_ISSUANCE') or evidence_paths.get('IPE_08')
            render_download_controls("IPE_08_ISSUANCE", issuance_df, issuance_evidence_path, "IPE_08_ISSUANCE_Evidence.zip", "dl_ipe08")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_08"), language="sql")
        
        with c6:
            st.metric("Voucher Usage (IPE_08_USAGE)", f"{len(data.get('IPE_08_USAGE', data.get('DOC_VOUCHER_USAGE', pd.DataFrame()))):,} rows")
            display_source_badge(source_info.get("IPE_08_USAGE", source_info.get("DOC_VOUCHER_USAGE", "No Data")))
            usage_df = data.get('IPE_08_USAGE', data.get('DOC_VOUCHER_USAGE', pd.DataFrame()))
            usage_evidence_path = evidence_paths.get("IPE_08_USAGE") or evidence_paths.get("DOC_VOUCHER_USAGE")
            render_download_controls("IPE_08_USAGE", usage_df, usage_evidence_path, "IPE_08_USAGE_Evidence.zip", "dl_doc_voucher")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("DOC_VOUCHER_USAGE"), language="sql")

        c7, _, _ = st.columns(3)
        with c7:
            st.metric("Voucher Timing (IPE_08_TIMING)", f"{len(data.get('IPE_08_TIMING', pd.DataFrame())):,} rows")
            display_source_badge(source_info.get("IPE_08_TIMING", "No Data"))
            ipe08_timing_evidence_path = evidence_paths.get("IPE_08_TIMING")
            render_download_controls("IPE_08_TIMING", data.get('IPE_08_TIMING', pd.DataFrame()), ipe08_timing_evidence_path, "IPE_08_TIMING_Evidence.zip", "dl_ipe08_timing")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_08_TIMING"), language="sql")

        st.markdown("**Supporting IPE Extracts**")

        c8, c9, c10, c11 = st.columns(4)
        with c8:
            st.metric("Customer Prepayments (IPE_10)", f"{len(data.get('IPE_10', pd.DataFrame())):,} rows")
            display_source_badge(source_info.get("IPE_10", "No Data"))
            ipe10_evidence_path = evidence_paths.get("IPE_10")
            render_download_controls("IPE_10", data.get('IPE_10', pd.DataFrame()), ipe10_evidence_path, "IPE_10_Evidence.zip", "dl_ipe10")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_10"), language="sql")

        with c9:
            st.metric("Delivered Not Reconciled (IPE_12)", f"{len(data.get('IPE_12', pd.DataFrame())):,} rows")
            display_source_badge(source_info.get("IPE_12", "No Data"))
            ipe12_evidence_path = evidence_paths.get("IPE_12")
            render_download_controls("IPE_12", data.get('IPE_12', pd.DataFrame()), ipe12_evidence_path, "IPE_12_Evidence.zip", "dl_ipe12")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_12"), language="sql")

        with c10:
            st.metric("Collection Accounts (IPE_31)", f"{len(data.get('IPE_31', pd.DataFrame())):,} rows")
            display_source_badge(source_info.get("IPE_31", "No Data"))
            ipe31_evidence_path = evidence_paths.get("IPE_31")
            render_download_controls("IPE_31", data.get('IPE_31', pd.DataFrame()), ipe31_evidence_path, "IPE_31_Evidence.zip", "dl_ipe31")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_31"), language="sql")

        with c11:
            st.metric("Marketplace Refunds (IPE_34)", f"{len(data.get('IPE_34', pd.DataFrame())):,} rows")
            display_source_badge(source_info.get("IPE_34", "No Data"))
            ipe34_evidence_path = evidence_paths.get("IPE_34")
            render_download_controls("IPE_34", data.get('IPE_34', pd.DataFrame()), ipe34_evidence_path, "IPE_34_Evidence.zip", "dl_ipe34")
            with st.expander("View Source Query"):
                st.code(get_sql_query_for_item("IPE_34"), language="sql")

        c12, _, _ = st.columns(3)
        with c12:
            st.metric("Jdash Export (JDASH)", f"{len(jdash_df):,} rows")
            if "Fixture" in jdash_source:
                display_source_badge("Local Fixture")
            elif "Uploaded" in jdash_source or "File" in jdash_source:
                display_source_badge("Uploaded File")
            else:
                display_source_badge("No Data")
            st.caption(f"Source detail: {jdash_source}")
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
            c2.dataframe(proof_df.head(50), width="stretch")

        # --- TASK 2: VTC (Acceptance Criteria #3 - Glass Box) ---
        with tabs[1]:
            # Logic Explanation Block
            with st.expander("📖 Logic Explanation", expanded=False):
                st.info(VTC_LOGIC)

            cat_cr03 = categorize_vouchers(
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

            source_keys = vtc_metrics.get("source_unique_voucher_keys", 0)
            target_keys = vtc_metrics.get("target_unique_voucher_keys", 0)
            matched_source = vtc_metrics.get("matched_source_vouchers", 0)
            st.caption(
                f"Key Match Check: source keys={source_keys:,} | target keys={target_keys:,} | matched source rows={matched_source:,}"
            )

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
            c2.dataframe(proof_df_vtc.head(50), width="stretch")

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
                st.dataframe(proof_df_reclass, width="stretch")

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
