import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock

# --- CONFIGURATION DU CHEMIN ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# --- IMPORTS DU BACKEND ---
from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager
from src.utils.fx_utils import FXConverter
from src.bridges.classifier import (
    _categorize_nav_vouchers,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
    calculate_integration_error_adjustment
)

app = FastAPI(
    title="SOXauto C-PG-1 API",
    description="Backend API for n8n orchestration. Executes live extractions and classification logic.",
    version="1.0.0"
)

# --- MODÈLES DE DONNÉES (Input n8n) ---

class AuditRequest(BaseModel):
    country: str = Field(..., description="Code pays cible (ex: 'JD_GH', 'EC_NG')")
    cutoff_date: str = Field(..., description="Date de clôture au format YYYY-MM-DD")
    # Données Jdash optionnelles (requises uniquement pour Task 1)
    jdash_data: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Données brutes de l'export Jdash (liste de JSON objects) pour la Tâche 1"
    )

# --- FONCTIONS UTILITAIRES (Backend Logic) ---

def _get_sql_params(country: str, cutoff_date_str: str) -> Dict[str, str]:
    """Prépare les paramètres SQL standardisés."""
    dt = pd.to_datetime(cutoff_date_str)
    year = dt.year
    month = dt.month
    return {
        "cutoff_date": cutoff_date_str,
        "year_start": f"{year}-{month:02d}-01",
        "year_end": cutoff_date_str,
        "year": str(year),
        "month": str(month),
        "gl_accounts": "('15010','18303','18304','18406','18408','18409','18411','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')",
        "id_companies_active": f"('{country}')"
    }

def _run_extraction(item_id: str, params: Dict[str, str]) -> pd.DataFrame:
    """
    Exécute l'extraction live via IPERunner.
    Génère automatiquement les preuves (Evidence Package) sur le disque du serveur.
    """
    # Mock AWS car on utilise l'ODBC direct via Env Var
    mock_secrets = MagicMock(spec=AWSSecretsManager)
    mock_secrets.get_secret.return_value = "FAKE_SECRET"

    item = get_item_by_id(item_id)
    if not item:
        raise ValueError(f"Item {item_id} introuvable dans le catalogue.")

    # Injection manuelle des paramètres (Robustesse)
    final_query = item.sql_query
    for key, value in params.items():
        if f"{{{key}}}" in final_query:
            final_query = final_query.replace(f"{{{key}}}", str(value))
            
    ipe_config = {
        'id': item.item_id,
        'description': getattr(item, 'description', ""),
        'secret_name': "fake",
        'main_query': final_query,
        'validation': {}
    }

    # Configuration du Runner avec métadonnées pour le dossier de preuves
    period = params["cutoff_date"].replace("-", "")[:6]
    country = params["id_companies_active"].strip("()'")
    
    runner = IPERunner(
        ipe_config, 
        mock_secrets, 
        cutoff_date=params["cutoff_date"],
        country=country,
        period=period,
        full_params=params
    )

    try:
        print(f"🚀 [API] Extracting {item_id} for {country}...")
        df = runner.run() # Déclenche l'extraction ET la génération de preuves
        
        # Filtrage de sécurité par pays
        for col in ['ID_COMPANY', 'id_company', 'ID_Company', 'country']:
            if col in df.columns:
                df = df[df[col] == country].copy()
                break
        return df
    except Exception as e:
        print(f"❌ [API] Extraction failed for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed for {item_id}: {str(e)}")

def _get_fx_converter(params: Dict[str, str]):
    """Charge les taux FX (CR_05) et initialise le convertisseur."""
    try:
        df_cr05 = _run_extraction("CR_05", params)
        return FXConverter(df_cr05)
    except Exception as e:
        print(f"⚠️ [API] FX Warning: {e}")
        # Retourne un convertisseur vide qui ne fera pas de conversion (fallback)
        return None 

# --- ENDPOINTS API ---

@app.get("/health")
def health_check():
    """Health check pour n8n ou Kubernetes."""
    return {"status": "online", "version": "1.0.0", "service": "soxauto-cpg1"}

@app.post("/run-audit/task1-timing")
def run_task1(req: AuditRequest):
    """
    Exécute la Tâche 1 : Timing Difference.
    Nécessite les données Jdash dans le corps de la requête (JSON).
    """
    if not req.jdash_data:
        raise HTTPException(status_code=400, detail="Le champ 'jdash_data' est requis pour la Tâche 1.")
    
    params = _get_sql_params(req.country, req.cutoff_date)
    
    # 1. Extraction Live
    df_ipe08 = _run_extraction("IPE_08", params)
    fx_converter = _get_fx_converter(params)
    
    # 2. Chargement Données Manuelles (Jdash) depuis le JSON
    df_jdash = pd.DataFrame(req.jdash_data)

    # 3. Exécution Logique
    bridge_amt, proof_df = calculate_timing_difference_bridge(
        jdash_df=df_jdash,
        ipe_08_df=df_ipe08,
        cutoff_date=req.cutoff_date,
        fx_converter=fx_converter
    )

    return {
        "task": "Timing Difference",
        "amount_usd": bridge_amt,
        "proof_count": len(proof_df),
        # On limite la taille du JSON de retour pour n8n (les 1000 premiers cas)
        "proof_data": proof_df.head(1000).to_dict(orient="records")
    }

@app.post("/run-audit/task2-vtc")
def run_task2(req: AuditRequest):
    """
    Exécute la Tâche 2 : VTC Adjustment.
    Déclenche l'extraction de CR_03, IPE_08 et DOC_VOUCHER_USAGE.
    """
    params = _get_sql_params(req.country, req.cutoff_date)

    # 1. Extraction Live
    df_cr03 = _run_extraction("CR_03", params)
    df_ipe08 = _run_extraction("IPE_08", params)
    df_usage = _run_extraction("DOC_VOUCHER_USAGE", params)
    fx_converter = _get_fx_converter(params)

    # 2. Pré-traitement (Catégorisation)
    cat_cr03 = _categorize_nav_vouchers(
        cr_03_df=df_cr03,
        ipe_08_df=df_ipe08,
        doc_voucher_usage_df=df_usage
    )

    # 3. Exécution Logique
    adj_amt, proof_df, vtc_metrics = calculate_vtc_adjustment(
        ipe_08_df=df_ipe08,
        categorized_cr_03_df=cat_cr03,
        fx_converter=fx_converter
    )

    return {
        "task": "VTC Adjustment",
        "amount_usd": adj_amt,
        "proof_count": len(proof_df),
        "proof_data": proof_df.head(1000).to_dict(orient="records"),
        "vtc_metrics": vtc_metrics,
    }

@app.post("/run-audit/task3-integration")
def run_task3(req: AuditRequest):
    """
    Exécute la Tâche 3 : Integration Errors.
    """
    params = _get_sql_params(req.country, req.cutoff_date)

    df_errors = _run_extraction("IPE_REC_ERRORS", params)
    fx_converter = _get_fx_converter(params)

    adj_amt, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df=df_errors,
        fx_converter=fx_converter
    )

    return {
        "task": "Integration Errors",
        "amount_usd": adj_amt,
        "proof_count": len(proof_df),
        "proof_data": proof_df.head(1000).to_dict(orient="records")
    }

@app.post("/run-audit/task4-reclass")
def run_task4(req: AuditRequest):
    """
    Exécute la Tâche 4 : Customer Reclass.
    """
    params = _get_sql_params(req.country, req.cutoff_date)

    df_ipe07 = _run_extraction("IPE_07", params)
    
    # Pas de FX nécessaire pour cette tâche (identification)
    bridge_amt, proof_df = calculate_customer_posting_group_bridge(df_ipe07)

    return {
        "task": "Customer Reclass",
        "amount_usd": bridge_amt, # Toujours 0
        "proof_count": len(proof_df),
        "proof_data": proof_df.head(1000).to_dict(orient="records")
    }