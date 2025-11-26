import os
import sys
import pandas as pd
import asyncio
from datetime import datetime
from unittest.mock import MagicMock

# Ajout du chemin src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager

# === CONFIGURATION ===
PARAMS = {
    "cutoff_date": "2025-09-30",
    "year_start": "2025-09-01",
    "year_end": "2025-09-30",
    "year": 2025,
    "month": 9,
    "gl_accounts": "('15010','18303','18304','18406','18408','18409','18411','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')",
    "id_companies_active": "('EC_NG')" # TEST SUR NIGERIA
}

ITEMS_TO_FETCH = [
    "CR_04",
    "CR_03",
    "IPE_07",
    "IPE_08",
    "DOC_VOUCHER_USAGE",
    "CR_05",           # <-- Celui qui posait problème
    "IPE_REC_ERRORS"
]

async def main():
    print("🚀 STARTING LIVE EXTRACTION via Service Account (With Evidence)...")
    output_dir = "tests/fixtures"
    
    # Mock Secret Manager
    mock_secrets = MagicMock(spec=AWSSecretsManager)
    mock_secrets.get_secret.return_value = "FAKE_CONNECTION_STRING"

    for item_id in ITEMS_TO_FETCH:
        print(f"\n--- Fetching {item_id} ---")
        try:
            item = get_item_by_id(item_id)
            if not item:
                print(f"❌ Item {item_id} not found.")
                continue

            # 1. Préparer la requête (Injection manuelle des paramètres)
            final_query = item.sql_query
            for key, value in PARAMS.items():
                if f"{{{key}}}" in final_query:
                    final_query = final_query.replace(f"{{{key}}}", str(value))
            
            # 2. Configurer le runner
            ipe_config = {
                'id': item.item_id,
                'description': getattr(item, 'description', f"Extraction for {item.item_id}"),
                'secret_name': "fake_secret",
                'main_query': final_query,
                'validation': {} 
            }

            runner = IPERunner(
                ipe_config=ipe_config,
                secret_manager=mock_secrets,
                cutoff_date=PARAMS["cutoff_date"],
                # On passe les infos pour le dossier de preuves
                country="EC_NG", 
                period="202509",
                full_params=PARAMS
            )

            # === PATCH CRITIQUE POUR CR_05 ===
            # On remplace la méthode _execute_query_with_parameters de cette instance
            # pour qu'elle ignore les '?' (qui sont dans les noms de colonnes)
            # et n'envoie AUCUN paramètre au driver ODBC.
            original_exec = runner._execute_query_with_parameters
            
            def patched_exec(query, params=None):
                # On force params à vide car on a déjà tout injecté dans final_query
                return pd.read_sql(query, runner.connection)
            
            runner._execute_query_with_parameters = patched_exec
            # =================================

            # 3. Exécuter (Ceci va générer les preuves ET retourner le DF)
            print(f"   Executing Runner (Extraction + Evidence Generation)...")
            df = runner.run()

            # 4. Sauvegarder le fixture pour les tests
            filename = f"fixture_{item_id}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)
            
            print(f"✅ SUCCESS: Saved {len(df)} rows to {filepath}")
            
            # Log des totaux pour vérification rapide
            if "Amount" in df.columns:
                print(f"   Total Amount: {df['Amount'].sum():,.2f}")
            elif "remaining_amount" in df.columns:
                print(f"   Total Remaining: {df['remaining_amount'].sum():,.2f}")

        except Exception as e:
            print(f"❌ ERROR fetching {item_id}: {str(e)}")
            # import traceback
            # traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())