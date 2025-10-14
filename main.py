# main.py
import pandas as pd
import pyodbc
import gspread
from google.oauth2.service_account import Credentials
import logging
from config import IPE_CONFIGS, DB_CONNECTIONS, GSHEET_NAME

# --- Configuration du Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Fonctions de Connexion ---
def get_db_connection(connection_name):
    """Crée et retourne une connexion à la base de données."""
    try:
        conn_str = DB_CONNECTIONS[connection_name]
        return pyodbc.connect(conn_str)
    except Exception as e:
        logging.error(f"Erreur de connexion à la base de données '{connection_name}': {e}")
        raise

def get_gsheet_client():
    """Crée et retourne un client pour interagir avec Google Sheets."""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        # Assurez-vous d'avoir un fichier credentials.json dans le même répertoire
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Erreur de connexion à Google Sheets: {e}")
        raise

# --- Fonction d'Écriture sur Google Sheets ---
def write_to_gsheet(client, data_df, tab_name):
    """Écrit un DataFrame Pandas dans un onglet spécifique d'un Google Sheet."""
    try:
        spreadsheet = client.open(GSHEET_NAME)
        try:
            worksheet = spreadsheet.worksheet(tab_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1", cols="1")

        # Convertir le DataFrame en liste de listes et l'écrire
        worksheet.update([data_df.columns.values.tolist()] + data_df.values.tolist())
        logging.info(f"Données écrites avec succès dans l'onglet '{tab_name}' du Google Sheet '{GSHEET_NAME}'.")
    except Exception as e:
        logging.error(f"Erreur lors de l'écriture sur Google Sheets: {e}")
        raise

# --- Cœur de la Logique d'Extraction et Validation ---
def run_ipe_extraction(ipe_config):
    """Exécute l'extraction et la validation pour une configuration IPE donnée."""
    ipe_id = ipe_config['id']
    logging.info(f"--- Début du traitement de l'IPE: {ipe_id} ---")

    try:
        conn = get_db_connection(ipe_config['db_connection_name'])
        
        # 1. Extraction des données principales
        logging.info(f"[{ipe_id}] Extraction des données principales...")
        main_query = ipe_config['main_query']
        df = pd.read_sql(main_query, conn)
        logging.info(f"[{ipe_id}] {len(df)} lignes extraites.")

        # 2. Validation de complétude
        logging.info(f"[{ipe_id}] Validation de complétude...")
        completeness_query = ipe_config['validation']['completeness_query'].format(main_query=main_query)
        expected_rows = pd.read_sql(completeness_query, conn).iloc[0, 0]
        if len(df) != expected_rows:
            raise Exception(f"Échec de la validation de complétude. Attendu: {expected_rows}, Obtenu: {len(df)}")
        logging.info(f"[{ipe_id}] Validation de complétude: SUCCÈS.")

        # 3. Validation d'exactitude (Positive)
        logging.info(f"[{ipe_id}] Validation d'exactitude (Positive)...")
        accuracy_pos_query = ipe_config['validation']['accuracy_positive_query'].format(main_query=main_query)
        pos_check_result = pd.read_sql(accuracy_pos_query, conn).iloc[0, 0]
        if pos_check_result == 0:
            raise Exception("Échec du test d'exactitude positif. La transaction témoin n'a pas été trouvée.")
        logging.info(f"[{ipe_id}] Validation d'exactitude (Positive): SUCCÈS.")

        # 4. Validation d'exactitude (Négative)
        logging.info(f"[{ipe_id}] Validation d'exactitude (Négative)...")
        # Pour le test négatif, il faut parfois modifier la requête principale.
        # Ici, nous supposons qu'une requête modifiée est fournie ou que le test peut être fait sur la requête de base.
        if 'accuracy_negative_query' in ipe_config['validation']:
            main_query_modified = main_query.replace("in ('13010','13009','13006','13005','13004','13003')", "in ('13010','13006','13005','13004','13003')") # Exemple pour IPE_07
            accuracy_neg_query = ipe_config['validation']['accuracy_negative_query'].format(main_query_modified=main_query_modified)
            neg_check_result = pd.read_sql(accuracy_neg_query, conn).iloc[0, 0]
            if neg_check_result > 0:
                raise Exception("Échec du test d'exactitude négatif. Une transaction exclue a été trouvée.")
            logging.info(f"[{ipe_id}] Validation d'exactitude (Négative): SUCCÈS.")

        conn.close()
        return df

    except Exception as e:
        logging.error(f"[{ipe_id}] ERREUR LORS DU TRAITEMENT: {e}")
        return None

# --- Orchestrateur ---
def main():
    """Fonction principale pour orchestrer l'extraction de tous les IPEs."""
    logging.info("===== DÉBUT DU WORKFLOW D'EXTRACTION DE DONNÉES =====")
    
    gsheet_client = get_gsheet_client()
    
    for ipe in IPE_CONFIGS:
        result_df = run_ipe_extraction(ipe)
        if result_df is not None:
            logging.info(f"Traitement de l'IPE {ipe['id']} terminé avec succès.")
            # Écrire les données validées dans un onglet du Google Sheet
            write_to_gsheet(gsheet_client, result_df, f"IPE_{ipe['id']}_Data")
        else:
            logging.error(f"Le traitement de l'IPE {ipe['id']} a échoué. Arrêt du workflow.")
            # Dans un vrai scénario, on enverrait une alerte ici.
            break # Arrête le processus en cas d'erreur sur un IPE

    logging.info("===== FIN DU WORKFLOW D'EXTRACTION DE DONNÉES =====")


if __name__ == "__main__":
    main()