import os
import sys
import pandas as pd
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Ajout du chemin src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager

# === CONFIGURATION ===
# Allowed entity codes (whitelist for security)
ALLOWED_ENTITIES = [
    'EC_NG',  # Nigeria
    'JD_GH',  # Ghana
    'EC_KE',  # Kenya
    'JM_EG',  # Egypt
    'EC_MA',  # Morocco
    'EC_CI',  # Ivory Coast
    'EC_SN',  # Senegal
    'EC_TN',  # Tunisia
    'EC_UG',  # Uganda
    'EC_ZA',  # South Africa
]

# Date configuration for SQL queries
CUTOFF_DATE = "2025-09-30"
YEAR_START = "2025-09-01"
YEAR_END = "2025-09-30"
YEAR = 2025
MONTH = 9

# GL Accounts to extract
GL_ACCOUNTS = "('15010','18303','18304','18406','18408','18409','18411','18416','18417','18419','18421','18320','18307','18308','18309','18312','18310','18314','18380','18635','18317','18318','18319')"

# Items to fetch from catalog
ITEMS_TO_FETCH = [
    "CR_04",
    "CR_03",
    "IPE_07",
    "IPE_08",
    "DOC_VOUCHER_USAGE",
    "CR_05",           # <-- Celui qui posait problème
    "IPE_REC_ERRORS"
]

def get_output_dir(entity: str) -> Path:
    """
    Get the output directory path for a given entity.
    
    Args:
        entity: Entity code (e.g., 'EC_NG', 'JD_GH')
        
    Returns:
        Path object for the entity-specific fixtures directory
    """
    return Path(__file__).parent.parent / "tests" / "fixtures" / entity


async def main(entity: str = "EC_NG") -> None:
    """
    Fetch live fixtures from SQL Server and save to entity-specific folders.
    
    This function connects to the SQL Server database (via mocked connection in this script)
    and extracts IPE/CR data for the specified entity. Data is saved as CSV files in 
    tests/fixtures/{entity}/ directory. Existing files like JDASH.csv are preserved.
    
    Args:
        entity: Entity code (e.g., 'EC_NG', 'JD_GH'). Must be in ALLOWED_ENTITIES whitelist.
        
    Raises:
        ValueError: If entity is not in the ALLOWED_ENTITIES whitelist.
    """
    # Security: Validate entity against whitelist to prevent SQL injection
    if entity not in ALLOWED_ENTITIES:
        raise ValueError(
            f"Invalid entity '{entity}'. Allowed entities: {', '.join(ALLOWED_ENTITIES)}"
        )
    
    print(f"🚀 STARTING LIVE EXTRACTION via Service Account (With Evidence) for entity: {entity}...")
    
    # Dynamic output path: tests/fixtures/{entity}/
    output_dir = get_output_dir(entity)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    
    # Configure PARAMS with entity-specific settings
    PARAMS = {
        "cutoff_date": CUTOFF_DATE,
        "year_start": YEAR_START,
        "year_end": YEAR_END,
        "year": YEAR,
        "month": MONTH,
        "gl_accounts": GL_ACCOUNTS,
        "id_companies_active": f"('{entity}')"
    }
    
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
                country=entity, 
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
            filepath = output_dir / filename
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
    parser = argparse.ArgumentParser(
        description="Fetch live fixtures from SQL Server and save to entity-specific folders"
    )
    parser.add_argument(
        "--entity",
        type=str,
        default="EC_NG",
        help="Entity code (e.g., EC_NG, JD_GH) to determine output folder"
    )
    args = parser.parse_args()
    
    asyncio.run(main(entity=args.entity))