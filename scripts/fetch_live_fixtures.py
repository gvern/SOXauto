import os
import sys
import pandas as pd
import asyncio
from datetime import datetime
from unittest.mock import MagicMock

# Ajout du chemin src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# CORRECTION ICI : On importe IPERunner, pas IPERunnerMSSQL
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
    # Note: Les parenthèses sont importantes pour le SQL "IN (...)"
    "gl_accounts": "('15010','18303','18304','18406','18408','18409','18411','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')",
    "id_companies_active": "('EC_NG')"
}

ITEMS_TO_FETCH = [
    #"CR_04",
    #"CR_03",
    "IPE_07",
    "IPE_08",
    "DOC_VOUCHER_USAGE",
    "IPE_REC_ERRORS"
]

async def main():
    print("🚀 STARTING LIVE EXTRACTION via Service Account...")
    output_dir = "tests/fixtures"
    
    # Mock Secret Manager (car on utilise ENV VAR pour la connexion)
    mock_secrets = MagicMock(spec=AWSSecretsManager)
    # Le runner a besoin que get_secret ne plante pas, même si on utilise la var d'env
    mock_secrets.get_secret.return_value = "FAKE_CONNECTION_STRING"

    for item_id in ITEMS_TO_FETCH:
        print(f"\n--- Fetching {item_id} ---")
        try:
            # 1. Récupérer l'item du catalogue
            item = get_item_by_id(item_id)
            if not item:
                print(f"❌ Item {item_id} not found in catalog.")
                continue

            # 2. Adapter l'item pour le Runner (qui attend un dict)
            # Le runner attend un dict avec 'id', 'description', 'secret_name', 'main_query'
            ipe_config = {
                'id': item.item_id,
                'description': getattr(item, 'description', f"Extraction for {item.item_id}"),
                'secret_name': "fake_secret", # On utilise la var d'env
                'main_query': item.sql_query,
                'validation': {} # Pas de validation SQL complexe pour ce test
            }

            # 3. Initialiser le runner
            runner = IPERunner(
                ipe_config=ipe_config,
                secret_manager=mock_secrets,
                cutoff_date=PARAMS["cutoff_date"]
            )

            # 4. Préparer les paramètres pour la requête
            # On remplace les placeholders {key} par les valeurs de PARAMS
            # Note: Le runner fait un .format() basique s'il y a des {}
            # Mais notre runner actuel attend des '?' pour pyodbc ou fait un format manuel.
            # Pour ce script de test, nous allons injecter les paramètres manuellement dans la requête
            # avant de la passer au runner, pour éviter les conflits de formatage.
            
            final_query = item.sql_query
            for key, value in PARAMS.items():
                if f"{{{key}}}" in final_query:
                    final_query = final_query.replace(f"{{{key}}}", str(value))
            
            # Mise à jour de la config du runner avec la requête formatée
            runner.config['main_query'] = final_query

            # 5. Exécuter (en passant None aux paramètres car on a déjà formaté la string)
            # Le runner va appeler _execute_query_with_parameters
            # Si la requête n'a plus de '?', on ne passe pas de params tuple.
            
            # Hack: on force l'exécution directe via la méthode interne pour contourner 
            # la logique de paramètres complexe du runner pour ce test rapide
            runner.connection = runner._get_database_connection()
            print(f"   Executing Runner (Extraction + Evidence Generation)...")            
            df = runner.run()
            
            # 6. Sauvegarder
            filename = f"fixture_{item_id}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)
            
            print(f"✅ SUCCESS: Saved {len(df)} rows to {filepath}")
            
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