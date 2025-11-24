import os
import sys
import pandas as pd
import pyodbc

# Configuration de la connexion (Reprend votre env var)
CONN_STR = os.environ.get("DB_CONNECTION_STRING")

# Liste des vues que nous avons identifiées dans IPE_REC_ERRORS.sql
VIEWS_TO_INSPECT = [
    "V_REC_3PL_MANUAL_TRANSACTIONS_ERRORS",
    "V_REC_CASHDEPOSIT_ERRORS",
    "V_REC_COLLECTIONADJ_ERRORS",
    "V_REC_INTERNATIONAL_DELIVERY_FEES_ERRORS",
    "V_REC_EXC_ACCOUNT_STATEMENTS_ERRORS",
    "V_REC_JFORCE_PAYOUTS_ERRORS",
    "V_REC_JPAYAPP_TRANSACTIONS_ERRORS",
    "V_REC_SC_TRANSACTIONS_CUSTOMER_ERRORS",
    "V_REC_PAYMENT_RECONCILES_ERRORS",
    "V_REC_PREPAID_DELIVERIES_ERRORS",
    "V_REC_CUSTOMER_PRE_PAYMENTS_ERRORS",
    "V_REC_CUSTOMER_REFUNDS_ERRORS",
    "V_REC_SC_TRANSACTIONS_ERRORS",
    "V_REC_SC_ACCOUNTSTATEMENTS_ERRORS",
    "V_REC_VENDOR_PAYMENTS_ERRORS"
]

def get_columns_for_view(cursor, view_name):
    try:
        # On essaie d'abord dans AIG_Nav_Jumia_Reconciliation
        query = f"""
        SELECT COLUMN_NAME 
        FROM [AIG_Nav_Jumia_Reconciliation].INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{view_name}'
        """
        cursor.execute(query)
        columns = [row[0] for row in cursor.fetchall()]
        
        # Si vide, on essaie sans préciser la DB (au cas où ce serait dbo)
        if not columns:
            query = f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{view_name}'
            """
            cursor.execute(query)
            columns = [row[0] for row in cursor.fetchall()]
            
        return columns
    except Exception as e:
        return [f"ERROR: {str(e)}"]

def main():
    if not CONN_STR:
        print("❌ Erreur: DB_CONNECTION_STRING n'est pas définie.")
        return

    print("🚀 Connexion à la base de données pour inspection des schémas...")
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        
        print("\n--- RÉSULTATS DE L'INSPECTION ---")
        for view in VIEWS_TO_INSPECT:
            cols = get_columns_for_view(cursor, view)
            print(f"\nVIEW: {view}")
            if cols:
                print(f"COLUMNS: {', '.join(cols)}")
            else:
                print("❌ Table introuvable ou pas de colonnes.")
                
        conn.close()
        print("\n✅ Inspection terminée.")
        
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")

if __name__ == "__main__":
    main()