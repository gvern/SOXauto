# main.py
"""
Orchestrateur principal pour l'automatisation du processus SOX PG-01.
Point d'entrée compatible avec Google Cloud Run.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Flask, request

from config import (
    GCP_PROJECT_ID, 
    IPE_CONFIGS, 
    BIGQUERY_DATASET, 
    BIGQUERY_RESULTS_TABLE_PREFIX,
    GOOGLE_DRIVE_FOLDER_ID
)
from gcp_utils import initialize_gcp_services, get_drive_manager
from ipe_runner import IPERunner, IPEValidationError, IPEConnectionError

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation de Flask pour Cloud Run
app = Flask(__name__)


class WorkflowExecutionError(Exception):
    """Exception levée en cas d'échec du workflow global."""
    pass


def execute_ipe_workflow(cutoff_date: str = None) -> Tuple[Dict[str, Any], int]:
    """
    Exécute le workflow complet d'extraction et validation des IPEs.
    
    Args:
        cutoff_date: Date de coupure optionnelle (format YYYY-MM-DD)
        
    Returns:
        Tuple contenant (résultats, code_statut_HTTP)
    """
    workflow_start_time = datetime.now()
    logger.info("===== DÉBUT DU WORKFLOW D'AUTOMATISATION SOX PG-01 =====")
    
    # Résultats globaux du workflow
    workflow_results = {
        'workflow_id': f"SOXauto_PG01_{workflow_start_time.strftime('%Y%m%d_%H%M%S')}",
        'start_time': workflow_start_time.isoformat(),
        'cutoff_date': cutoff_date,
        'ipe_results': {},
        'summary': {
            'total_ipes': len(IPE_CONFIGS),
            'successful_ipes': 0,
            'failed_ipes': 0,
            'total_rows_processed': 0
        }
    }
    
    try:
        # 1. Initialiser les services GCP
        logger.info("Initialisation des services Google Cloud...")
        secret_manager, bigquery_client = initialize_gcp_services(GCP_PROJECT_ID)
        
        # 2. Traiter chaque IPE
        for ipe_config in IPE_CONFIGS:
            ipe_id = ipe_config['id']
            ipe_result = {
                'status': 'PENDING',
                'start_time': datetime.now().isoformat(),
                'rows_extracted': 0,
                'validation_summary': {},
                'error_message': None
            }
            
            try:
                logger.info(f"--- Traitement de l'IPE: {ipe_id} ---")
                
                # Créer et exécuter le runner IPE
                runner = IPERunner(
                    ipe_config=ipe_config,
                    secret_manager=secret_manager,
                    cutoff_date=cutoff_date
                )
                
                # Exécuter l'extraction et validation
                validated_data = runner.run()
                
                # Stocker les résultats dans BigQuery
                table_id = f"{BIGQUERY_RESULTS_TABLE_PREFIX}_{ipe_id.lower()}"
                bigquery_client.write_dataframe(
                    dataframe=validated_data,
                    dataset_id=BIGQUERY_DATASET,
                    table_id=table_id
                )
                
                # Mettre à jour les résultats
                ipe_result.update({
                    'status': 'SUCCESS',
                    'end_time': datetime.now().isoformat(),
                    'rows_extracted': len(validated_data),
                    'validation_summary': runner.get_validation_summary(),
                    'bigquery_table': f"{BIGQUERY_DATASET}.{table_id}"
                })
                
                workflow_results['summary']['successful_ipes'] += 1
                workflow_results['summary']['total_rows_processed'] += len(validated_data)
                
                logger.info(f"IPE {ipe_id} traité avec succès - {len(validated_data)} lignes")
                
            except (IPEValidationError, IPEConnectionError) as e:
                ipe_result.update({
                    'status': 'FAILED',
                    'end_time': datetime.now().isoformat(),
                    'error_message': str(e)
                })
                workflow_results['summary']['failed_ipes'] += 1
                
                logger.error(f"Échec du traitement de l'IPE {ipe_id}: {e}")
                
                # En cas d'échec critique, arrêter le workflow
                workflow_results['end_time'] = datetime.now().isoformat()
                workflow_results['overall_status'] = 'FAILED'
                workflow_results['failure_reason'] = f"Échec critique sur l'IPE {ipe_id}"
                
                # Envoyer une alerte (à implémenter selon vos besoins)
                _send_failure_alert(workflow_results)
                
                return workflow_results, 500
                
            except Exception as e:
                ipe_result.update({
                    'status': 'ERROR',
                    'end_time': datetime.now().isoformat(),
                    'error_message': f"Erreur inattendue: {str(e)}"
                })
                workflow_results['summary']['failed_ipes'] += 1
                
                logger.error(f"Erreur inattendue lors du traitement de l'IPE {ipe_id}: {e}")
                
                # Continuer avec les autres IPE en cas d'erreur non critique
                
            finally:
                workflow_results['ipe_results'][ipe_id] = ipe_result
        
        # 3. Finaliser le workflow
        workflow_results['end_time'] = datetime.now().isoformat()
        
        if workflow_results['summary']['failed_ipes'] == 0:
            workflow_results['overall_status'] = 'SUCCESS'
            logger.info("===== WORKFLOW TERMINÉ AVEC SUCCÈS =====")
            
            # Créer un log d'audit complet
            _create_audit_log(secret_manager, workflow_results)
            
            return workflow_results, 200
        else:
            workflow_results['overall_status'] = 'PARTIAL_SUCCESS'
            logger.warning("===== WORKFLOW TERMINÉ AVEC ÉCHECS PARTIELS =====")
            return workflow_results, 206  # Partial Content
            
    except Exception as e:
        workflow_results.update({
            'end_time': datetime.now().isoformat(),
            'overall_status': 'ERROR',
            'error_message': f"Erreur fatale du workflow: {str(e)}"
        })
        
        logger.error(f"Erreur fatale du workflow: {e}")
        _send_failure_alert(workflow_results)
        
        return workflow_results, 500


def _send_failure_alert(workflow_results: Dict[str, Any]) -> None:
    """
    Envoie une alerte en cas d'échec du workflow.
    À adapter selon vos besoins (email, Slack, etc.)
    """
    try:
        # Placeholder pour l'envoi d'alertes
        # Vous pouvez implémenter ici l'envoi d'emails, notifications Slack, etc.
        logger.critical("ALERTE: Échec du workflow SOX PG-01")
        logger.critical(f"Détails: {json.dumps(workflow_results, indent=2)}")
        
        # Exemple d'implémentation future:
        # send_email_alert(workflow_results)
        # send_slack_notification(workflow_results)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi d'alerte: {e}")


def _create_audit_log(secret_manager, workflow_results: Dict[str, Any]) -> None:
    """
    Crée un log d'audit complet du workflow.
    """
    try:
        # Créer le gestionnaire Google Drive si configuré
        if GOOGLE_DRIVE_FOLDER_ID:
            try:
                drive_manager = get_drive_manager(secret_manager, "GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
                audit_log_id = drive_manager.create_audit_log(GOOGLE_DRIVE_FOLDER_ID, workflow_results)
                logger.info(f"Log d'audit créé: {audit_log_id}")
            except Exception as e:
                logger.warning(f"Impossible de créer le log d'audit sur Drive: {e}")
        
        # Log local en backup
        logger.info(f"Résumé du workflow: {json.dumps(workflow_results['summary'], indent=2)}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du log d'audit: {e}")


@app.route('/', methods=['POST'])
def cloud_run_handler():
    """
    Point d'entrée pour Google Cloud Run.
    Accepte les requêtes HTTP POST avec des paramètres optionnels.
    """
    try:
        # Récupérer les paramètres de la requête
        request_data = request.get_json() or {}
        cutoff_date = request_data.get('cutoff_date')
        
        # Exécuter le workflow
        results, status_code = execute_ipe_workflow(cutoff_date)
        
        return results, status_code
        
    except Exception as e:
        error_response = {
            'error': 'Erreur interne du serveur',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }
        logger.error(f"Erreur du gestionnaire Cloud Run: {e}")
        return error_response, 500


@app.route('/health', methods=['GET'])
def health_check():
    """Point de contrôle de santé pour Cloud Run."""
    return {
        'status': 'healthy',
        'service': 'SOXauto-PG01',
        'timestamp': datetime.now().isoformat()
    }, 200


@app.route('/config', methods=['GET'])
def get_configuration():
    """Retourne la configuration actuelle (sans les secrets)."""
    config_info = {
        'project_id': GCP_PROJECT_ID,
        'bigquery_dataset': BIGQUERY_DATASET,
        'configured_ipes': [
            {
                'id': ipe['id'],
                'description': ipe['description']
            }
            for ipe in IPE_CONFIGS
        ],
        'total_ipes': len(IPE_CONFIGS)
    }
    return config_info, 200


def main_workflow_local(cutoff_date: str = None):
    """
    Point d'entrée pour l'exécution locale (développement/test).
    
    Args:
        cutoff_date: Date de coupure optionnelle
    """
    results, status = execute_ipe_workflow(cutoff_date)
    
    print("\n" + "="*60)
    print("RÉSULTATS DU WORKFLOW SOX PG-01")
    print("="*60)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("="*60)
    
    return results


if __name__ == "__main__":
    # Exécution locale pour développement
    import sys
    
    cutoff_date_param = None
    if len(sys.argv) > 1:
        cutoff_date_param = sys.argv[1]
    
    try:
        main_workflow_local(cutoff_date_param)
    except KeyboardInterrupt:
        logger.info("Workflow interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution locale: {e}")
        sys.exit(1)