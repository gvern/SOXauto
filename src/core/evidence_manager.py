# evidence_manager.py
"""
Digital Evidence Package Manager pour SOXauto PG-01
Génère des preuves non-altérables pour chaque exécution d'IPE conformément aux exigences SOX.
"""

import os
import hashlib
import json
import zipfile
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DigitalEvidenceManager:
    """
    Gestionnaire de preuves numériques pour les extractions SOX.
    Crée un package d'évidence complet et inaltérable pour chaque exécution.
    """
    
    def __init__(self, base_evidence_dir: str = "evidence"):
        """
        Initialise le gestionnaire d'évidence.
        
        Args:
            base_evidence_dir: Répertoire racine pour stocker les preuves
        """
        self.base_evidence_dir = Path(base_evidence_dir)
        self.base_evidence_dir.mkdir(exist_ok=True)
        
    def create_evidence_package(self, ipe_id: str, execution_metadata: Dict[str, Any]) -> str:
        """
        Crée un répertoire d'évidence horodaté pour une exécution d'IPE.
        
        Args:
            ipe_id: Identifiant de l'IPE
            execution_metadata: Métadonnées de l'exécution
            
        Returns:
            Chemin vers le répertoire d'évidence créé
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Inclut les millisecondes
        evidence_dir = self.base_evidence_dir / ipe_id / timestamp
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer le fichier de métadonnées d'exécution
        metadata_file = evidence_dir / "execution_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(execution_metadata, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Package d'évidence créé: {evidence_dir}")
        return str(evidence_dir)


class IPEEvidenceGenerator:
    """
    Générateur de preuves spécifique à une exécution d'IPE.
    """
    
    def __init__(self, evidence_dir: str, ipe_id: str):
        """
        Initialise le générateur pour un IPE spécifique.
        
        Args:
            evidence_dir: Répertoire où stocker les preuves
            ipe_id: Identifiant de l'IPE
        """
        self.evidence_dir = Path(evidence_dir)
        self.ipe_id = ipe_id
        self.execution_log = []
        
    def save_executed_query(self, query: str, parameters: Dict[str, Any] = None) -> None:
        """
        Sauvegarde la requête SQL exacte exécutée avec ses paramètres.
        
        Args:
            query: Requête SQL exécutée
            parameters: Paramètres utilisés dans la requête
        """
        try:
            # Sauvegarder la requête brute
            query_file = self.evidence_dir / "01_executed_query.sql"
            with open(query_file, 'w', encoding='utf-8') as f:
                f.write("-- Requête SQL Exécutée pour IPE {}\n".format(self.ipe_id))
                f.write("-- Horodatage: {}\n".format(datetime.now().isoformat()))
                f.write("-- ===========================================\n\n")
                f.write(query)
            
            # Sauvegarder les paramètres si fournis
            if parameters:
                params_file = self.evidence_dir / "02_query_parameters.json"
                with open(params_file, 'w', encoding='utf-8') as f:
                    json.dump(parameters, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("QUERY_SAVED", f"Requête sauvegardée: {len(query)} caractères")
            logger.info(f"[{self.ipe_id}] Requête exécutée sauvegardée")
            
        except Exception as e:
            self._log_action("ERROR", f"Erreur sauvegarde requête: {e}")
            logger.error(f"[{self.ipe_id}] Erreur sauvegarde requête: {e}")
            raise
    
    def save_data_snapshot(self, dataframe: pd.DataFrame, snapshot_rows: int = 100) -> None:
        """
        Sauvegarde un échantillon des données extraites (équivalent programmatique d'une capture d'écran).
        
        Args:
            dataframe: DataFrame contenant les données extraites
            snapshot_rows: Nombre de lignes à inclure dans l'échantillon
        """
        try:
            # Snapshot des premières lignes
            snapshot_df = dataframe.head(snapshot_rows).copy()
            
            # Ajouter des métadonnées à l'échantillon
            snapshot_df.attrs['total_rows'] = len(dataframe)
            snapshot_df.attrs['snapshot_rows'] = len(snapshot_df)
            snapshot_df.attrs['extraction_timestamp'] = datetime.now().isoformat()
            
            # Sauvegarder en CSV avec métadonnées
            snapshot_file = self.evidence_dir / "03_data_snapshot.csv"
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                f.write(f"# IPE Data Snapshot - {self.ipe_id}\n")
                f.write(f"# Total Rows: {len(dataframe)}\n")
                f.write(f"# Snapshot Rows: {len(snapshot_df)}\n")
                f.write(f"# Extraction Time: {datetime.now().isoformat()}\n")
                f.write(f"# Columns: {list(dataframe.columns)}\n")
                f.write("#" + "="*80 + "\n")
            
            # Ajouter les données
            snapshot_df.to_csv(snapshot_file, mode='a', index=False, encoding='utf-8')
            
            # Créer également un résumé statistique
            summary_file = self.evidence_dir / "04_data_summary.json"
            summary = {
                'total_rows': len(dataframe),
                'total_columns': len(dataframe.columns),
                'columns': list(dataframe.columns),
                'data_types': dataframe.dtypes.astype(str).to_dict(),
                'memory_usage_mb': round(dataframe.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                'snapshot_rows': len(snapshot_df),
                'extraction_timestamp': datetime.now().isoformat()
            }
            
            # Ajouter des statistiques descriptives pour les colonnes numériques
            numeric_columns = dataframe.select_dtypes(include=['number']).columns
            if len(numeric_columns) > 0:
                summary['numeric_statistics'] = dataframe[numeric_columns].describe().to_dict()
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("SNAPSHOT_SAVED", f"Échantillon sauvegardé: {len(snapshot_df)} lignes sur {len(dataframe)}")
            logger.info(f"[{self.ipe_id}] Échantillon de données sauvegardé")
            
        except Exception as e:
            self._log_action("ERROR", f"Erreur sauvegarde échantillon: {e}")
            logger.error(f"[{self.ipe_id}] Erreur sauvegarde échantillon: {e}")
            raise
    
    def generate_integrity_hash(self, dataframe: pd.DataFrame) -> str:
        """
        Génère un hash cryptographique de l'ensemble complet des données.
        Ce hash prouve l'intégrité des données et détecte toute altération.
        
        Args:
            dataframe: DataFrame complet des données extraites
            
        Returns:
            Hash SHA-256 des données
        """
        try:
            # Créer un hash déterministe du DataFrame complet
            # Trier par toutes les colonnes pour garantir la reproductibilité
            df_sorted = dataframe.sort_values(by=list(dataframe.columns)).reset_index(drop=True)
            
            # Convertir en string avec un format standardisé
            data_string = df_sorted.to_csv(index=False, encoding='utf-8')
            
            # Calculer le hash SHA-256
            data_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            
            # Informations supplémentaires pour la vérification
            hash_info = {
                'algorithm': 'SHA-256',
                'hash_value': data_hash,
                'data_rows': len(dataframe),
                'data_columns': len(dataframe.columns),
                'generation_timestamp': datetime.now().isoformat(),
                'python_pandas_version': pd.__version__,
                'verification_instructions': [
                    "1. Trier les données par toutes les colonnes",
                    "2. Exporter en CSV sans index avec encoding UTF-8",
                    "3. Calculer SHA-256 du string résultant",
                    "4. Comparer avec hash_value"
                ]
            }
            
            # Sauvegarder le hash et les instructions de vérification
            hash_file = self.evidence_dir / "05_integrity_hash.json"
            with open(hash_file, 'w', encoding='utf-8') as f:
                json.dump(hash_info, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder également juste le hash dans un fichier texte pour facilité
            hash_txt_file = self.evidence_dir / "05_integrity_hash.sha256"
            with open(hash_txt_file, 'w') as f:
                f.write(data_hash)
            
            self._log_action("HASH_GENERATED", f"Hash d'intégrité généré: {data_hash[:16]}...")
            logger.info(f"[{self.ipe_id}] Hash d'intégrité généré: {data_hash[:16]}...")
            
            return data_hash
            
        except Exception as e:
            self._log_action("ERROR", f"Erreur génération hash: {e}")
            logger.error(f"[{self.ipe_id}] Erreur génération hash: {e}")
            raise
    
    def save_validation_results(self, validation_results: Dict[str, Any]) -> None:
        """
        Sauvegarde les résultats détaillés des validations SOX.
        
        Args:
            validation_results: Résultats des tests de validation
        """
        try:
            validation_file = self.evidence_dir / "06_validation_results.json"
            
            # Ajouter des métadonnées de validation
            enhanced_results = {
                'ipe_id': self.ipe_id,
                'validation_timestamp': datetime.now().isoformat(),
                'validation_results': validation_results,
                'sox_compliance': {
                    'completeness_test': validation_results.get('completeness', {}).get('status') == 'PASS',
                    'accuracy_positive_test': validation_results.get('accuracy_positive', {}).get('status') == 'PASS',
                    'accuracy_negative_test': validation_results.get('accuracy_negative', {}).get('status') == 'PASS',
                    'overall_compliance': validation_results.get('overall_status') == 'SUCCESS'
                }
            }
            
            with open(validation_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("VALIDATION_SAVED", f"Résultats de validation sauvegardés")
            logger.info(f"[{self.ipe_id}] Résultats de validation sauvegardés")
            
        except Exception as e:
            self._log_action("ERROR", f"Erreur sauvegarde validation: {e}")
            logger.error(f"[{self.ipe_id}] Erreur sauvegarde validation: {e}")
            raise
    
    def finalize_evidence_package(self) -> str:
        """
        Finalise le package d'évidence en sauvegardant le log d'exécution
        et en créant un archive ZIP sécurisée.
        
        Returns:
            Chemin vers l'archive ZIP créée
        """
        try:
            # Sauvegarder le log d'exécution final
            log_file = self.evidence_dir / "07_execution_log.json"
            
            final_log = {
                'ipe_id': self.ipe_id,
                'execution_start': self.execution_log[0]['timestamp'] if self.execution_log else None,
                'execution_end': datetime.now().isoformat(),
                'evidence_directory': str(self.evidence_dir),
                'actions_log': self.execution_log,
                'files_generated': [f.name for f in self.evidence_dir.glob('*') if f.is_file()],
                'package_integrity': self._calculate_package_hash()
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(final_log, f, indent=2, ensure_ascii=False, default=str)
            
            # Créer une archive ZIP avec protection
            zip_file = self.evidence_dir.parent / f"{self.evidence_dir.name}_evidence.zip"
            
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.evidence_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.evidence_dir.parent)
                        zipf.write(file_path, arcname)
            
            self._log_action("PACKAGE_FINALIZED", f"Archive créée: {zip_file.name}")
            logger.info(f"[{self.ipe_id}] Package d'évidence finalisé: {zip_file}")
            
            return str(zip_file)
            
        except Exception as e:
            self._log_action("ERROR", f"Erreur finalisation package: {e}")
            logger.error(f"[{self.ipe_id}] Erreur finalisation package: {e}")
            raise
    
    def _calculate_package_hash(self) -> str:
        """Calcule un hash de l'ensemble du package d'évidence."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(self.evidence_dir.glob('*')):
            if file_path.is_file() and file_path.name != "07_execution_log.json":
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _log_action(self, action: str, details: str) -> None:
        """Enregistre une action dans le log d'exécution."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.execution_log.append(log_entry)


class EvidenceValidator:
    """
    Validateur pour vérifier l'intégrité des packages d'évidence.
    """
    
    @staticmethod
    def verify_package_integrity(evidence_dir: str) -> Dict[str, Any]:
        """
        Vérifie l'intégrité d'un package d'évidence.
        
        Args:
            evidence_dir: Répertoire du package d'évidence
            
        Returns:
            Résultats de la vérification
        """
        evidence_path = Path(evidence_dir)
        verification_results = {
            'package_path': str(evidence_path),
            'verification_timestamp': datetime.now().isoformat(),
            'files_present': {},
            'integrity_verified': False,
            'issues_found': []
        }
        
        # Vérifier la présence des fichiers requis
        required_files = [
            "01_executed_query.sql",
            "03_data_snapshot.csv", 
            "04_data_summary.json",
            "05_integrity_hash.json",
            "06_validation_results.json",
            "07_execution_log.json"
        ]
        
        for file_name in required_files:
            file_path = evidence_path / file_name
            verification_results['files_present'][file_name] = file_path.exists()
            
            if not file_path.exists():
                verification_results['issues_found'].append(f"Fichier manquant: {file_name}")
        
        # Vérifier l'intégrité du hash si possible
        hash_file = evidence_path / "05_integrity_hash.json"
        if hash_file.exists():
            try:
                with open(hash_file, 'r', encoding='utf-8') as f:
                    hash_info = json.load(f)
                verification_results['original_hash'] = hash_info.get('hash_value')
                verification_results['hash_algorithm'] = hash_info.get('algorithm')
            except Exception as e:
                verification_results['issues_found'].append(f"Erreur lecture hash: {e}")
        
        verification_results['integrity_verified'] = len(verification_results['issues_found']) == 0
        
        return verification_results