import pandas as pd
import os

def inspect_columns():
    # Chemin vers vos données extraites
    fixtures_dir = os.path.join("tests", "fixtures")
    
    # Les fichiers critiques pour le Bridge Timing Difference
    files_to_check = [
        "fixture_IPE_08.csv",          # Source A (Issuance)
        "fixture_DOC_VOUCHER_USAGE.csv", # Source B (Usage TV) - pour info
        "fixture_JDASH.csv"            # Source C (Jdash) - pour info
    ]

    print("=== 🔍 INSPECTION DES COLONNES DISPONIBLES ===")

    for filename in files_to_check:
        filepath = os.path.join(fixtures_dir, filename)
        
        if os.path.exists(filepath):
            try:
                # On lit juste l'en-tête pour aller vite
                df = pd.read_csv(filepath, nrows=0)
                print(f"\n📂 Fichier : {filename}")
                print("-" * 50)
                # Affichage propre de la liste
                print(f"Nombre de colonnes : {len(df.columns)}")
                print(list(df.columns))
            except Exception as e:
                print(f"❌ Erreur lors de la lecture de {filename}: {e}")
        else:
            print(f"\n⚠️ Fichier introuvable : {filename}")

if __name__ == "__main__":
    inspect_columns()