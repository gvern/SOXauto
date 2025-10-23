# Guide d'Exécution et de Paramétrage des Extractions SQL

Ce guide explique comment exécuter les scripts de génération de fichiers et comment paramétrer les requêtes SQL avec des dates dynamiques.

---

## 1. Principe de Fonctionnement

Toutes les requêtes SQL sont stockées dans le catalogue (`src/core/catalog/cpg1.py`) et contiennent des **placeholders** comme `{cutoff_date}`.

Avant d'être exécutées, ces requêtes sont "rendues" (rendered) : les placeholders sont remplacés par les valeurs des **variables d'environnement** correspondantes via `src/utils/sql_template.py`.

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

### b) Lancer l'Orchestrateur

```bash
python3 scripts/run_full_reconciliation.py
```

Le pipeline exécute les générateurs (IPE_07, IPE_31, Other AR), puis la **classification des écarts** (bridges) et produit `data/outputs/bridges_classified.csv`.

### c) Exécuter un Seul Fichier (Débogage)

```bash
# Exemple: IPE_07 (Customer Accounts)
python3 scripts/generate_customer_accounts.py

# Exécuter un sous-ensemble via le runner générique
python3 scripts/run_sql_from_catalog.py --only IPE_07,CR_04
```

---

## 4. Gestion des Erreurs et Débogage

La fonction `render_sql` lève une erreur si des placeholders restent non résolus (ex: `{cutoff_date}` manquant). Cela évite des erreurs SQL obscures.

Pour diagnostiquer une exécution:

1. Ouvrez le package de preuves généré: `evidence/<IPE_ID>/<timestamp>/`
2. Consultez `01_executed_query.sql` pour voir la requête exécutée et `02_query_parameters.json` pour les paramètres.

---

## 5. Notes Opérationnelles

- La connexion SQL Server utilise `DB_CONNECTION_STRING` (recommandé) ou `MSSQL_*` (serveur, base, user, password). Voir `docs/setup/DATABASE_CONNECTION.md`.
- Les scripts écrivent les CSV dans `data/outputs/` et génèrent un package de preuves complet (8 fichiers) par IPE.
- La classification des "Bridges & Adjustments" est décrite dans `docs/development/BRIDGES_RULES.md`.

---

## 6. Référence Fichiers

- Catalogue SQL: `src/core/catalog/cpg1.py`
- Rendu SQL: `src/utils/sql_template.py`
- Générateurs: `scripts/generate_customer_accounts.py`, `scripts/generate_collection_accounts.py`, `scripts/generate_other_ar.py`
- Orchestrateur: `scripts/run_full_reconciliation.py`
- Runner générique: `scripts/run_sql_from_catalog.py`
