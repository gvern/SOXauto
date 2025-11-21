# Documentation - Système d'Évidence Digitale SOX

## 🛡️ Vue d'Ensemble

Le système d'évidence digitale de SOXauto PG-01 génère automatiquement des preuves inaltérables pour chaque exécution d'IPE, dépassant largement les exigences des captures d'écran manuelles traditionnelles.

### Avantages par rapport au Processus Manuel

| Aspect | Processus Manuel | SOXauto Digital Evidence |
|--------|------------------|---------------------------|
| **Intégrité** | Capture d'écran (altérable) | Hash cryptographique (inaltérable) |
| **Complétude** | Première page seulement | Dataset complet + échantillon |
| **Traçabilité** | Requête non documentée | Requête exacte + paramètres |
| **Validation** | Vérification manuelle | Tests automatisés + résultats |
| **Stockage** | Fichiers dispersés | Package structuré |
| **Vérification** | Impossibilité de re-vérifier | Vérification cryptographique possible |
| **Versioning** | Aucune version de code | Git commit hash + contexte système |

---

## 📦 Composition du Package d'Évidence

Chaque exécution d'IPE génère un dossier horodaté contenant 8 fichiers de preuve :

### Nouveau: Naming Convention
Format du dossier : `{ipe_id}_{country}_{period}_{timestamp}`
- Exemple: `IPE_08_NG_202509_20251120_103000`
- `ipe_id`: Identifiant de l'IPE (ex: IPE_08)
- `country`: Code pays (ex: NG pour Nigeria, KE pour Kenya)
- `period`: Période au format YYYYMM (ex: 202509 pour Septembre 2025)
- `timestamp`: Horodatage au format YYYYMMDD_HHMMSS

### 0. `00_system_context.json` (NOUVEAU)
**Rôle :** Contexte système pour la traçabilité complète
```json
{
  "git_commit_id": "a1b2c3d",
  "execution_host": "soxauto-worker-01",
  "python_version": "3.11.4 (main, Jun  7 2023, 10:13:09) [GCC 9.4.0]",
  "runner_version": "SOXauto v1.0"
}
```

### 1. `01_executed_query.sql`
**Rôle :** Preuve de la requête exacte exécutée
```sql
-- Requête SQL Exécutée pour IPE IPE_07
-- Horodatage: 2024-10-15T14:30:25.123456
-- ===========================================

SELECT vl.[id_company], vl.[Entry No_], ...
FROM [dbo].[Customer Ledger Entries] vl
WHERE [Posting Date] < ?
  AND [Document Type] in ('13010','13009'...)
```

### 2. `02_query_parameters.json` (AMÉLIORÉ)
**Rôle :** TOUS les paramètres utilisés dans la requête (pas seulement cutoff_date)
```json
{
  "cutoff_date": "2024-05-01",
  "parameters": ["2024-05-01", "2024-05-01", "2024-05-01"],
  "gl_accounts": "13003,13011,18350",
  "id_companies_active": "BF,CI,DZ,EG,GH,KE,MA,NG,SN,UG",
  "year": "2024",
  "month": "05",
  "execution_timestamp": "2024-10-15T14:30:25.123456"
}
```

### 3. `03_data_snapshot.csv` (AMÉLIORÉ - TAIL)
**Rôle :** Échantillon des DERNIÈRES données (tail au lieu de head)
```csv
# IPE Data Snapshot - IPE_07
# Total Rows: 12547
# Snapshot Rows (TAIL): 1000
# Extraction Time: 2024-10-15T14:30:27.456789
# Columns: ['id_company', 'Entry No_', 'Document No_', ...]
################################################################################
id_company,Entry No_,Document No_,Document Type,...
BF,123456,DOC001,13010,...
CI,789012,DOC002,13009,...
```
**Note :** 
- Si le dataset contient > 1000 lignes : les 1000 DERNIÈRES lignes sont sauvegardées (tail)
- Si le dataset contient ≤ 1000 lignes : toutes les lignes sont sauvegardées

### 4. `04_data_summary.json` (AMÉLIORÉ)
**Rôle :** Statistiques descriptives des données extraites
```json
{
  "total_rows": 12547,
  "total_columns": 25,
  "columns": ["id_company", "Entry No_", "Document No_", ...],
  "data_types": {"id_company": "object", "Entry No_": "int64", ...},
  "memory_usage_mb": 15.7,
  "snapshot_rows": 1000,
  "snapshot_type": "tail",
  "extraction_timestamp": "2024-10-15T14:30:28.123456",
  "numeric_statistics": {
    "Entry No_": {"mean": 156789.5, "std": 45123.2, ...}
  }
}
```

### 5. `05_integrity_hash.json`
**Rôle :** Hash cryptographique prouvant l'intégrité des données (INNOVATION MAJEURE)
```json
{
  "algorithm": "SHA-256",
  "hash_value": "a1b2c3d4e5f6789012345...",
  "data_rows": 12547,
  "data_columns": 25,
  "generation_timestamp": "2024-10-15T14:30:28.789012",
  "verification_instructions": [
    "1. Trier les données par toutes les colonnes",
    "2. Exporter en CSV sans index avec encoding UTF-8",
    "3. Calculer SHA-256 du string résultant",
    "4. Comparer avec hash_value"
  ]
}
```

### 6. `06_validation_results.json`
**Rôle :** Résultats détaillés des tests SOX
```json
{
  "ipe_id": "IPE_07",
  "validation_timestamp": "2024-10-15T14:30:30.123456",
  "validation_results": {
    "completeness": {"status": "PASS", "expected_count": 12547, "actual_count": 12547},
    "accuracy_positive": {"status": "PASS", "witness_count": 1},
    "accuracy_negative": {"status": "PASS", "excluded_count": 0}
  },
  "sox_compliance": {
    "completeness_test": true,
    "accuracy_positive_test": true,
    "accuracy_negative_test": true,
    "overall_compliance": true
  }
}
```

### 7. `07_execution_log.json`
**Rôle :** Journal complet de l'exécution
```json
{
  "ipe_id": "IPE_07",
  "execution_start": "2024-10-15T14:30:25.123456",
  "execution_end": "2024-10-15T14:30:35.789012",
  "evidence_directory": "/evidence/IPE_07/20241015_143025_123",
  "actions_log": [
    {"timestamp": "2024-10-15T14:30:25.200", "action": "QUERY_SAVED", "details": "..."},
    {"timestamp": "2024-10-15T14:30:27.500", "action": "SNAPSHOT_SAVED", "details": "..."},
    {"timestamp": "2024-10-15T14:30:28.800", "action": "HASH_GENERATED", "details": "..."}
  ],
  "package_integrity": "f9e8d7c6b5a4321098765..."
}
```

---

## 🔐 Sécurité et Inaltérabilité

### Hash Cryptographique SHA-256
**Innovation majeure :** Chaque dataset est "empreint" par un hash SHA-256 qui :
- **Détecte toute altération** : Modifier un seul caractère change complètement le hash
- **Prouve l'authenticité** : Le hash original ne peut être recalculé sans les données exactes
- **Permet la vérification** : N'importe qui peut re-calculer le hash pour vérifier l'intégrité

### Process de Vérification
```python
# Pour vérifier l'intégrité d'un dataset :
import pandas as pd
import hashlib

# 1. Charger les données suspectes
df = pd.read_csv("data_to_verify.csv")

# 2. Trier exactement comme lors de la génération
df_sorted = df.sort_values(by=list(df.columns)).reset_index(drop=True)

# 3. Générer le hash
data_string = df_sorted.to_csv(index=False, encoding='utf-8')
calculated_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

# 4. Comparer avec le hash original
original_hash = "a1b2c3d4e5f6789012345..."  # Du fichier d'évidence
if calculated_hash == original_hash:
    print("✅ DONNÉES INTÈGRES - Aucune altération détectée")
else:
    print("❌ DONNÉES ALTÉRÉES - Les données ont été modifiées")
```

### Archive ZIP Protégée
Chaque package est finalisé dans une archive ZIP contenant :
- Tous les 7 fichiers d'évidence
- Un hash du package complet
- Protection contre l'altération accidentelle

---

## 📊 Valeur Ajoutée pour les Auditeurs

### Supériorité sur les Captures d'Écran

1. **Complétude** : Au lieu de voir 20 lignes, l'auditeur a accès à l'échantillon + statistiques du dataset complet

2. **Vérifiabilité** : Contrairement à une image, l'auditeur peut :
   - Re-exécuter la requête pour comparer
   - Vérifier le hash pour prouver l'intégrité
   - Analyser les statistiques pour détecter des anomalies

3. **Traçabilité** : Chaque étape est documentée avec horodatage précis

4. **Non-répudiation** : Le hash cryptographique constitue une preuve légale

### Exemple d'Audit Trail
```
📁 evidence_sox_pg01/
  └── 📁 IPE_07/
      └── 📁 20241015_143025_123/
          ├── 📄 01_executed_query.sql
          ├── 📄 02_query_parameters.json  
          ├── 📄 03_data_snapshot.csv
          ├── 📄 04_data_summary.json
          ├── 📄 05_integrity_hash.json
          ├── 📄 06_validation_results.json
          └── 📄 07_execution_log.json
      └── 📁 20241115_143025_456/  # Exécution suivante
          └── ...
  └── 📁 CR_03_04/
      └── ...

📄 IPE_07_20241015_143025_123_evidence.zip  # Archive finale
```

---

## 🚀 Intégration dans le Workflow

### Automatisation Transparente
```python
# Dans main.py - Intégration transparente
evidence_manager = DigitalEvidenceManager("evidence_sox_pg01")

runner = IPERunner(
    ipe_config=ipe_config,
    secret_manager=secret_manager,
    cutoff_date=cutoff_date,
    evidence_manager=evidence_manager  # ← Évidence automatique
)

validated_data = runner.run()  # ← Package d'évidence généré automatiquement
```

### Stockage et Archivage
1. **Local** : Répertoire `evidence_sox_pg01/` structuré par IPE et date
2. **Cloud** : Upload automatique vers Google Drive/S3 pour archivage
3. **Archive** : ZIP horodaté pour chaque exécution

---

## 📋 Checklist Auditeur

### Vérification d'un Package d'Évidence

✅ **Fichiers présents** : Les 7 fichiers requis sont présents  
✅ **Horodatage cohérent** : Tous les timestamps sont dans une fenêtre logique  
✅ **Hash d'intégrité** : Le hash peut être recalculé et correspond  
✅ **Validations SOX** : Tous les tests sont PASS  
✅ **Requête documentée** : La requête SQL est complète et paramétrisée  
✅ **Échantillon représentatif** : Le snapshot reflète les statistiques globales  

### Script de Validation Automatique
```python
from evidence_manager import EvidenceValidator

# Vérifier un package d'évidence
results = EvidenceValidator.verify_package_integrity("evidence/IPE_07/20241015_143025_123")

if results['integrity_verified']:
    print("✅ Package d'évidence VALIDE")
else:
    print("❌ Problèmes détectés:")
    for issue in results['issues_found']:
        print(f"   - {issue}")
```

---

## 🎯 Conclusion

Ce système d'évidence digitale transforme SOXauto PG-01 en un outil de niveau enterprise qui :

- **Dépasse les standards** des captures d'écran manuelles
- **Fournit des preuves cryptographiques** incontestables
- **Facilite le travail des auditeurs** avec une documentation complète
- **Garantit la conformité SOX** avec traçabilité totale
- **Protège l'organisation** contre les contestations d'intégrité des données

**Résultat :** Un processus d'audit automatisé qui inspire confiance et résiste à tout défi d'intégrité.