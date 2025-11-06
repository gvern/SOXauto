# Guide d'Exécution et de Paramétrage des Extractions SQL

Ce guide explique comment exécuter les extractions IPE via Temporal et comment paramétrer les requêtes SQL avec des dates dynamiques.

---

## 1. Principe de Fonctionnement

Toutes les requêtes SQL sont stockées dans le catalogue (`src/core/catalog/cpg1.py`) et contiennent des **placeholders** comme `{cutoff_date}`.

L'orchestration est gérée par **Temporal.io**, qui exécute les workflows et activities de manière durable et fiable. Avant l'exécution des requêtes, les placeholders sont remplacés par les valeurs des **variables d'environnement** correspondantes via `src/utils/sql_template.py`.

---

## 2. Paramètres Disponibles

Les paramètres suivants sont reconnus par les scripts. Exportez-les dans votre terminal avant d'exécuter une extraction.

| Variable d'Environnement | Format Requis                   | Description                                             | Utilisé par |
|--------------------------|---------------------------------|---------------------------------------------------------|-------------|
| `CUTOFF_DATE`            | `AAAA-MM-JJ`                    | Date de clôture (exclusive) pour la plupart des IPEs.   | IPE_07, IPE_10, IPE_31… |
| `YEAR_START`             | `AAAA-MM-JJ`                    | Début de période annuelle pour les rapports consolidés. | CR_04       |
| `YEAR_END`               | `AAAA-MM-JJ`                    | Fin de période annuelle pour les rapports consolidés.   | CR_04       |
| `FX_DATE`                | `AAAA-MM-JJ HH:MM:SS.mmm`       | Date exacte pour les taux de change.                    | CR_05a      |

---

## 3. Exemple: Clôture de Septembre 2025

### a) Configurer l'Environnement

Pour une clôture au 30/09/2025, la `CUTOFF_DATE` est le premier jour du mois suivant.

```bash
# Date de clôture (exclusive)
export CUTOFF_DATE='2025-10-01'

# Période annuelle (ex: 2025)
export YEAR_START='2025-01-01'
export YEAR_END='2025-12-31'

# Taux de change (si requis par CR_05a)
export FX_DATE='2025-09-30 00:00:00.000'
```

Astuce: Placez ces variables dans un fichier `.env` et sourcez-le.

### b) Lancer le Temporal Worker

Le worker Temporal exécute les workflows d'extraction IPE de manière durable et fiable.

```bash
# Démarrer le Temporal Worker
python -m src.orchestrators.cpg1_worker
```

Le worker se connecte à Temporal et attend que des workflows soient déclenchés. Les workflows peuvent être déclenchés manuellement ou via des schedules Temporal configurés pour exécuter automatiquement les extractions mensuelles.

### c) Déclencher un Workflow Manuellement (Débogage)

```bash
# Exemple: Déclencher un workflow d'extraction via Temporal CLI
tctl workflow start \
  --taskqueue soxauto-tasks \
  --workflow_type IPEExtractionWorkflow \
  --input '"2025-10-01"'

# Ou via un script Python
python -c "
from temporalio.client import Client
import asyncio

async def trigger_workflow():
    client = await Client.connect('localhost:7233')
    result = await client.execute_workflow(
        'IPEExtractionWorkflow',
        args=['2025-10-01'],
        id='extraction-sept-2025',
        task_queue='soxauto-tasks'
    )
    print(f'Workflow result: {result}')

asyncio.run(trigger_workflow())
"
```

**Note**: Les anciens scripts (`scripts/run_full_reconciliation.py`, `scripts/generate_*.py`) sont obsolètes et remplacés par l'orchestration Temporal.

---

## 4. Gestion des Erreurs et Débogage

La fonction `render_sql` lève une erreur si des placeholders restent non résolus (ex: `{cutoff_date}` manquant). Cela évite des erreurs SQL obscures.

Pour diagnostiquer une exécution:

1. Consultez le **Temporal Web UI** (`http://localhost:8080` ou Temporal Cloud) pour voir l'état du workflow
2. Ouvrez le package de preuves généré: `evidence/<IPE_ID>/<timestamp>/`
3. Consultez `01_executed_query.sql` pour voir la requête exécutée et `02_query_parameters.json` pour les paramètres
4. Vérifiez les logs du Temporal Worker pour les erreurs d'exécution

---

## 5. Notes Opérationnelles

- L'orchestration est gérée par **Temporal.io** pour une exécution durable et fiable
- La connexion SQL Server utilise un tunnel **Teleport (`tsh`)** sécurisé vers `fin-sql.jumia.local`
- Les packages de preuves complets (8 fichiers) sont générés automatiquement par IPE dans `evidence/<IPE_ID>/`
- La classification des "Bridges & Adjustments" est décrite dans `docs/development/BRIDGES_RULES.md`
- Le Temporal Web UI permet de surveiller l'état de tous les workflows en temps réel

---

## 6. Référence Fichiers

- Catalogue SQL: `src/core/catalog/cpg1.py`
- Rendu SQL: `src/utils/sql_template.py`
- Temporal Worker: `src/orchestrators/cpg1_worker.py`
- Workflows Temporal: `src/orchestrators/workflow.py`
- IPE Runner: `src/core/runners/mssql_runner.py`
