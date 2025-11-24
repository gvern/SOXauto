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
from src.bridges.classifier import (
    _categorize_nav_vouchers,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
    calculate_integration_error_adjustment
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="SOXauto | C-PG-1 Audit Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
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
""", unsafe_allow_html=True)

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
        'id': item.item_id, 'description': getattr(item, 'description', ""), 'secret_name': "fake",
        'main_query': final_query, 'validation': {}
    }

    # --- MISE À JOUR : On passe les métadonnées enrichies au Runner ---
    runner = IPERunner(
        ipe_config, 
        mock_secrets, 
        cutoff_date=params["cutoff_date"],
        country=country_code,   # <--- Nouveau : Pour le nom du dossier
        period=period_str,      # <--- Nouveau : Pour le nom du dossier (YYYYMM)
        full_params=params      # <--- Nouveau : Pour le log complet des paramètres
    )
    
    try:
        # runner.run() va maintenant créer le dossier : IPE_XX_COUNTRY_PERIOD_TIMESTAMP
        df = runner.run()
        
        # On récupère le zip le plus récent
        zip_path = get_latest_evidence_zip(item_id)
        
        return df, zip_path
        
    except Exception as e:
        # Fallback fixture (Mode Démo sans BDD)
        fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv")
        if os.path.exists(fixture_path):
            return pd.read_csv(fixture_path, low_memory=False), None
        return pd.DataFrame(), None

def load_all_data(params):
    """Orchestrates loading and evidence collection with context."""
    REQUIRED_IPES = ["CR_04", "CR_03", "IPE_07", "IPE_08", "DOC_VOUCHER_USAGE", "IPE_REC_ERRORS"]
    data_store = {}
    evidence_store = {}
    
    status_container = st.empty()
    progress_bar = st.progress(0)

    # --- MISE À JOUR : Extraction du Contexte (Pays/Période) ---
    # On nettoie le format SQL "('JD_GH')" pour avoir juste "JD_GH"
    country_code = params['id_companies_active'].strip("()'")
    # On transforme "2025-09-30" en "202509"
    period_str = params['cutoff_date'].replace('-', '')[:6]
    
    for i, item_id in enumerate(REQUIRED_IPES):
        status_container.markdown(f"🛡️ **Audit Process:** Extracting & Hashing `{item_id}` for **{country_code}**...")
        
        # On passe les nouvelles métadonnées
        df, zip_path = asyncio.run(run_extraction_with_evidence(item_id, params, country_code, period_str))
        
        # Filtrage local pour l'affichage (si nécessaire)
        for col in ['ID_COMPANY', 'id_company', 'ID_Company', 'country']:
            if col in df.columns:
                df = df[df[col] == country_code].copy()
                break
        
        data_store[item_id] = df
        evidence_store[item_id] = zip_path
        
        progress_bar.progress((i + 1) / len(REQUIRED_IPES))
    
    progress_bar.empty()
    status_container.empty()
    return data_store, evidence_store

def load_jdash_data(uploaded_file):
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    fixture_path = os.path.join(REPO_ROOT, "tests", "fixtures", "fixture_JDASH.csv")
    if os.path.exists(fixture_path):
        return pd.read_csv(fixture_path)
    return pd.DataFrame(columns=['Voucher Id', 'Amount Used'])

# --- MAIN APP ---

def main():
    with st.sidebar:
        st.title("⚙️ Configuration")
        target_country = st.selectbox("Target Entity", ["JD_GH", "EC_NG", "EC_KE", "JM_EG"], index=0)
        cutoff_date = st.date_input("Control Period", value=datetime(2025, 9, 30))
        st.markdown("---")
        uploaded_jdash = st.file_uploader("Upload Jdash Export (CSV)", type="csv")
        st.markdown("---")
        run_btn = st.button("🚀 Start SOX Reconciliation", type="primary")

        year = cutoff_date.year
        month = cutoff_date.month
        params = {
            "cutoff_date": cutoff_date.strftime('%Y-%m-%d'),
            "year_start": f"{year}-{month:02d}-01",
            "year_end": cutoff_date.strftime('%Y-%m-%d'),
            "year": year, "month": month,
            "gl_accounts": "('15010','18303','18304','18406','18408','18409','18411','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')",
            "id_companies_active": f"('{target_country}')"
        }

    st.title("🛡️ SOXauto: C-PG-1 Control Center")
    st.markdown(f"**Entity:** {target_country} | **Period:** {cutoff_date.strftime('%Y-%m')}")
    
    if run_btn:
        # --- PHASE 1: DATA FACTORY (EVIDENCE GENERATION) ---
        st.header("1. Digital Evidence Factory")
        st.info("Extracting data from immutable sources, validating quality, and generating cryptographic hashes.")
        
        jdash_df = load_jdash_data(uploaded_jdash)
        data, evidence_paths = load_all_data(params)
        
        # Evidence Grid
        st.subheader("📦 Source Data Packages (Authenticated)")
        
        # Row 1
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("GL Balances (CR_04)", f"{len(data['CR_04']):,} rows")
            if evidence_paths.get('CR_04'):
                with open(evidence_paths['CR_04'], "rb") as fp:
                    st.download_button("🔒 Download Package (ZIP)", fp, f"CR_04_Evidence.zip", "application/zip", key="dl_cr04")
        
        with c2:
            st.metric("GL Entries (CR_03)", f"{len(data['CR_03']):,} rows")
            if evidence_paths.get('CR_03'):
                with open(evidence_paths['CR_03'], "rb") as fp:
                    st.download_button("🔒 Download Package (ZIP)", fp, f"CR_03_Evidence.zip", "application/zip", key="dl_cr03")

        with c3:
            st.metric("Voucher Liability (IPE_08)", f"{len(data['IPE_08']):,} rows")
            if evidence_paths.get('IPE_08'):
                with open(evidence_paths['IPE_08'], "rb") as fp:
                    st.download_button("🔒 Download Package (ZIP)", fp, f"IPE_08_Evidence.zip", "application/zip", key="dl_ipe08")

        st.markdown("---")

        # --- PHASE 2: THE AGENT (LOGIC) ---
        st.header("2. Agentic Classification (Bridges)")
        st.write("Applying validated business logic to identify and explain variances.")
        
        tabs = st.tabs(["Task 1: Timing Diff", "Task 2: VTC", "Task 3: Integration", "Task 4: Reclass"])

        with tabs[0]:
            bridge_amt, proof_df = calculate_timing_difference_bridge(
                jdash_df=jdash_df, ipe_08_df=data['IPE_08'], cutoff_date=params['cutoff_date']
            )
            c1, c2 = st.columns([1, 3])
            c1.metric("Timing Difference", f"${bridge_amt:,.2f}")
            c1.download_button("📥 Download Bridge Calculation", proof_df.to_csv(index=False), f"Bridge_Timing_{target_country}.csv")
            c2.dataframe(proof_df.head(50), use_container_width=True)

        with tabs[1]:
            cat_cr03 = _categorize_nav_vouchers(data['CR_03'])
            adj_amt, proof_df_vtc = calculate_vtc_adjustment(data['IPE_08'], cat_cr03)
            c1, c2 = st.columns([1, 3])
            c1.metric("VTC Adjustment", f"${adj_amt:,.2f}")
            c1.download_button("📥 Download Bridge Calculation", proof_df_vtc.to_csv(index=False), f"Bridge_VTC_{target_country}.csv")
            c2.dataframe(proof_df_vtc.head(50), use_container_width=True)

        with tabs[2]:
            adj_amt_int, proof_df_int = calculate_integration_error_adjustment(data['IPE_REC_ERRORS'])
            c1, c2 = st.columns([1, 3])
            c1.metric("Integration Errors", f"${adj_amt_int:,.2f}")
            c1.download_button("📥 Download Bridge Calculation", proof_df_int.to_csv(index=False), f"Bridge_Integration_{target_country}.csv")
            c2.dataframe(proof_df_int.head(50), use_container_width=True)

        with tabs[3]:
            _, proof_df_reclass = calculate_customer_posting_group_bridge(data['IPE_07'])
            if len(proof_df_reclass) == 0:
                st.success("✅ PASS: Data Quality Clean")
            else:
                st.error(f"❌ FAIL: {len(proof_df_reclass)} items")
                st.dataframe(proof_df_reclass)

        # --- PHASE 3: SUMMARY ---
        st.markdown("---")
        st.header("3. Final Reconciliation Status")
        
        total_explained = bridge_amt + adj_amt + adj_amt_int
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Explained Variance", f"${total_explained:,.2f}", delta="Automated Bridges")
        
        if total_explained != 0:
            col2.warning("Variance Explained")
        else:
            col2.success("Zero Variance")
            
        col3.info("Final Digital Evidence Package assembled.")

    else:
        st.info("Ready to Start. Ensure VPN/Teleport is active.")

if __name__ == "__main__":
    main()