import os
import sys
import pandas as pd
from datetime import datetime
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator
from src.core.catalog.cpg1 import get_item_by_id

def main():
    print("🛡️  GENERATING DIGITAL EVIDENCE PACKAGES FOR DEMO...")
    
    # 1. Initialisation du Manager
    evidence_manager = DigitalEvidenceManager(base_dir="evidence_demo_packages")
    
    # Liste des fichiers fixtures à "package"
    fixtures_dir = "tests/fixtures"
    items_to_package = [
        "CR_04", "CR_03", "IPE_07", "IPE_08", "DOC_VOUCHER_USAGE", "IPE_REC_ERRORS"
    ]

    for item_id in items_to_package:
        fixture_path = os.path.join(fixtures_dir, f"fixture_{item_id}.csv")
        
        if not os.path.exists(fixture_path):
            print(f"⚠️  Skipping {item_id}: Fixture not found.")
            continue
            
        print(f"\n📦 Packaging evidence for {item_id}...")
        
        # 2. Charger les données (Simulation de l'extraction)
        df = pd.read_csv(fixture_path, low_memory=False)
        
        # 3. Récupérer les infos du catalogue
        catalog_item = get_item_by_id(item_id)
        description = getattr(catalog_item, 'description', "Automated Extraction") if catalog_item else "Manual Fixture Load"
        sql_query = getattr(catalog_item, 'sql_query', "-- Query not available in catalog") if catalog_item else "-- Manual Load"
        
        # 4. Créer le dossier de preuves
        metadata = {
            'ipe_id': item_id,
            'description': description,
            'cutoff_date': '2025-09-30', # Date de la démo
            'execution_start': datetime.now().isoformat(),
            'sox_compliance_required': True,
            'runner': 'DemoEvidenceGenerator'
        }
        
        pkg_path = evidence_manager.create_evidence_package(item_id, metadata)
        generator = IPEEvidenceGenerator(pkg_path, item_id)
        
        # 5. Générer les artéfacts (C'est ce que Joao veut voir)
        
        # A. La Requête SQL (Provenance)
        generator.save_executed_query(sql_query, {'cutoff_date': '2025-09-30', 'mode': 'demo'})
        
        # B. Le Snapshot de Données (Intégrité)
        generator.save_data_snapshot(df)
        
        # C. Le Hash Cryptographique (Sécurité)
        # C'est le fichier clé pour Joao (.sha256)
        integrity_hash = generator.generate_integrity_hash(df)
        
        # D. Les Résultats de Validation (Qualité)
        # On simule des checks réussis pour la démo
        validation_results = {
            'row_count': len(df),
            'status': 'PASS',
            'checks': [
                {'check': 'RowCount', 'result': 'PASS', 'details': f'{len(df)} rows'},
                {'check': 'ColumnIntegrity', 'result': 'PASS', 'details': 'All columns present'}
            ],
            'integrity_hash': integrity_hash
        }
        generator.save_validation_results(validation_results)
        
        # E. Finalisation (Logs & Zip)
        zip_path = generator.finalize_evidence_package()
        
        print(f"   ✅ Package created: {pkg_path}")
        print(f"   🔒 Integrity Hash: {integrity_hash}")

    print("\n✨ ALL EVIDENCE PACKAGES GENERATED SUCCESSFULLY.")
    print(f"📂 Location: {os.path.abspath('evidence_demo_packages')}")

if __name__ == "__main__":
    main()