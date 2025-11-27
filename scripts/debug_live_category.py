import pandas as pd
import sys
import os

# Ajout du path src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.bridges.classifier import _categorize_nav_vouchers

def main():
    # 1. Charger un petit échantillon du vrai fichier
    print("Chargement de fixture_CR_03.csv...")
    try:
        df = pd.read_csv("tests/fixtures/fixture_CR_03.csv", nrows=50, low_memory=False)
    except FileNotFoundError:
        print("Erreur: Fichier fixture_CR_03.csv introuvable.")
        return
    print(df.columns)
    print(f"Chargé {len(df)} lignes.")
    
    # 2. Exécuter la classification
    print("Exécution de _categorize_nav_vouchers...")
    res = _categorize_nav_vouchers(df)
    
    # 3. Analyser les résultats
    print("\n--- RÉSULTATS ---")
    if 'bridge_category' not in res.columns:
        print("ERREUR: La colonne 'bridge_category' n'a pas été créée !")
        return

    categorized_count = res['bridge_category'].notna().sum()
    print(f"Lignes catégorisées : {categorized_count} / {len(res)}")
    
    if categorized_count == 0:
        print("\n--- ANALYSE D'ÉCHEC (5 premières lignes) ---")
        for i, row in res.head(5).iterrows():
            user = str(row.get('User ID', ''))
            desc = str(row.get('Document Description', ''))
            amt = row.get('Amount', 0)
            
            print(f"Ligne {i}:")
            print(f"  User: '{user}'")
            print(f"  Desc: '{desc}'")
            print(f"  Amt:  {amt}")
            
            # Simulation manuelle des règles pour voir ce qui cloche
            is_integration = "NAV" in user.upper() and ("BATCH" in user.upper() or "SRVC" in user.upper())
            print(f"  -> Is Integration? {is_integration}")
            
            if amt < 0:
                is_refund = "REFUND" in desc.upper() or "RF_" in desc.upper()
                print(f"  -> Is Refund? {is_refund}")
    

if __name__ == "__main__":
    main()