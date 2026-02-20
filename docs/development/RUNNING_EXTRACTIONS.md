# Guide d'Exécution et de Paramétrage des Extractions SQL

Ce guide explique comment exécuter les extractions IPE via Apache Airflow et comment paramétrer les requêtes SQL avec des dates dynamiques.

---

## 1. Principe de Fonctionnement

Toutes les requêtes SQL sont stockées dans le catalogue (`src/core/catalog/cpg1.py`) et contiennent des **placeholders** comme `{cutoff_date}`.

L'orchestration est gérée par **Apache Airflow**, qui exécute les DAGs et tasks de manière planifiée et fiable. Avant l'exécution des requêtes, les placeholders sont remplacés par les valeurs des **variables d'environnement** correspondantes via `src/utils/sql_template.py`.

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

### b) Démarrer les services Airflow

Airflow orchestre les extractions IPE via un DAG dédié (mensuel ou à la demande).

```bash
# Initialiser la base Airflow (une seule fois)
airflow db init

# Créer un utilisateur admin (si nécessaire)
airflow users create \
  --username admin \
  --firstname SOX \
  --lastname Admin \
  --role Admin \
  --email admin@example.com

# Démarrer le scheduler
airflow scheduler

# Démarrer le webserver (dans un second terminal)
airflow webserver --port 8080
```

Airflow planifie et exécute les DAG runs. Les extractions peuvent être déclenchées manuellement via UI/CLI ou via un schedule mensuel.

### c) Déclencher un DAG Manuellement (Débogage)

```bash
# Exemple: déclencher un run avec une date de clôture
airflow dags trigger soxauto_cpg1_reconciliation \
  --conf '{"cutoff_date": "2025-10-01"}'

# Lister les DAGs disponibles
airflow dags list

# Vérifier l'état des runs
airflow dags list-runs -d soxauto_cpg1_reconciliation
```

**Note**: Les scripts historiques (`scripts/run_full_reconciliation.py`, `scripts/generate_*.py`) restent utiles pour tests ciblés, mais l'orchestration officielle passe par Airflow.

---

## 4. Gestion des Erreurs et Débogage

La fonction `render_sql` lève une erreur si des placeholders restent non résolus (ex: `{cutoff_date}` manquant). Cela évite des erreurs SQL obscures.

Pour diagnostiquer une exécution:

1. Consultez l'**Airflow UI** (`http://localhost:8080`) pour voir l'état du DAG run et des tasks
2. Ouvrez le package de preuves généré: `evidence/<IPE_ID>/<timestamp>/`
3. Consultez `01_executed_query.sql` pour voir la requête exécutée et `02_query_parameters.json` pour les paramètres
4. Vérifiez les logs des tasks Airflow pour les erreurs d'exécution

---

## 5. Notes Opérationnelles

- L'orchestration est gérée par **Apache Airflow** pour une exécution planifiée et fiable
- La connexion SQL Server utilise un tunnel **Teleport (`tsh`)** sécurisé vers `fin-sql.jumia.local`
- Les packages de preuves complets (8 fichiers) sont générés automatiquement par IPE dans `evidence/<IPE_ID>/`
- La classification des "Bridges & Adjustments" est décrite dans `docs/development/BRIDGES_RULES.md`
- L'Airflow UI permet de surveiller l'état des DAG runs et tasks en temps réel

---

## 6. Référence Fichiers

- Catalogue SQL: `src/core/catalog/cpg1.py`
- Rendu SQL: `src/utils/sql_template.py`
- DAG Airflow: `dags/` (orchestration mensuelle et déclenchement manuel)
- IPE Runner: `src/core/runners/mssql_runner.py`
