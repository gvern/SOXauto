# POC SOXauto — Plan d’action et liste des besoins

## Objectif

Réaliser un POC end-to-end démontrant la capacité à:

- extraire des IPE et données cibles (offline démo puis sources réelles),
- réconcilier vs GL, classifier les écarts (bridges),
- produire des livrables auditables (rapports, CSV classifiés, traces d’exécution),
- avec des critères de succès mesurables et reproductibles.

---

## 1) Ce dont j’ai besoin (checklist)

### Accès & Sécurité

- Compte AWS (Account ID, Region), rôle IAM assumable pour Athena/S3 (nom du rôle, permissions S3:Get/List, Athena StartQueryExecution/GetResults, Glue GetTable/GetDatabase).
- Okta (app OIDC ou SAML selon flux existant) et paramètres (issuer, client_id/secret ou IdP SSO, redirect si applicable). Voir `docs/setup/OKTA_AWS_SETUP.md` et `docs/setup/OKTA_QUICK_REFERENCE.md`.
- Endpoints et autorisations MSSQL si utilisés (host, port 1433, database, username/password/SSO). Script utile: `scripts/check_mssql_connection.py`.
- Emplacement et droits S3 pour les IPE et outputs (bucket, prefixes `raw/`, `processed/`, `evidence/`).

### Données & Référentiels

- 2–3 IPE « représentatifs » (format XLSX/CSV/TSV), plus un mapping minimal (onglet/colonnes, clés de jointure, formats de dates, devise/FX si pertinent). Exemple et conventions: `docs/development/RUNNING_EXTRACTIONS.md`.
- Échantillon GL (ou démo fournie) et clés d’alignement (GL account, période, entité, devise).
- Paramètres de classification Bridges (si spécifiques) ou adoption du catalogue par défaut dans `src/bridges/catalog.py` et `src/bridges/classifier.py`.

### Environnement d’exécution

- Python 3.10+ (idéalement 3.11) avec les dépendances de `requirements.txt`.
- Variables d’environnement/credentials:
  - AWS: `AWS_PROFILE` ou `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` (ou SSO/Okta).
  - Okta: variables selon votre mode (voir docs OKTA_* en setup).
  - DB: `MSSQL_*` si nécessaire.
  - Emplacements locaux: `data/credentials/` (non versionné) pour secrets temporaires.
- Optionnel: Docker (voir `Dockerfile`) pour exécutions reproductibles.

### Outils & Scripts clés

- Démo locale (offline): `scripts/run_demo.py` génère des rapports dans `data/outputs/`.
- Extractions & réconciliation end-to-end: `scripts/run_full_reconciliation.py`.
- Générateurs par domaine: `scripts/generate_collection_accounts.py`, `scripts/generate_customer_accounts.py`, `scripts/generate_other_ar.py`.
- Diagnostics: `scripts/check_mssql_connection.py`, `scripts/run_sql_from_catalog.py`.
- Tests: `pytest` (voir `tests/`), fumée: `tests/test_smoke_catalog_and_scripts.py`.

### Livrables attendus

- CSV classifié final: `data/outputs/*final_report_classified.csv`.
- Rapports texte: `data/outputs/*summary_report.txt`, `*full_pipeline_report.txt`.
- Dossier `evidence/` horodaté (traces, logs, extraits) prêt pour audit.
- Note de cadrage et checklists de validation.

---

## 2) Plan d’action (POC complet mais pragmatique)

### Phase 0 — « Quick Wins » offline (0,5 jour)

Objectif: montrer des résultats immédiats sans dépendances cloud.

- Lancer la démo locale via `scripts/run_demo.py`.
- Collecter les artefacts générés dans `data/outputs/` et un snapshot dans `evidence/`.
- Valider: présence d’un CSV classifié, rapports, et distribution de bridges non vide.

Critères de succès:

- Rapports et CSV générés sans erreurs.
- Taux de classification > 90% sur le dataset démo (indicatif).

### Phase 1 — Connectivité & SSO (0,5–1 jour)

Objectif: sécuriser les accès pour les sources réelles.

- Valider Okta/AWS SSO (docs `docs/setup/*OKTA*`).
- Vérifier Athena/Glue/S3 (catalogue accessible, requêtes simples OK).
- Tester MSSQL (si concerné) avec `scripts/check_mssql_connection.py`.

Livrables:

- Screenshot ou log de connexion réussie (athena/mssql).
- Fiche de paramétrage (rôle, base, schéma, buckets).

### Phase 2 — 1 IPE réel « pilote » (1 jour)

Objectif: un premier flux bout-en-bout sur un IPE réel.

- Déclarer l’IPE et le mapping minimal (onglet, colonnes, types) selon `docs/development/RUNNING_EXTRACTIONS.md`.
- Exécuter l’extraction et la réconciliation avec `scripts/run_full_reconciliation.py`.
- Produire `*_summary_report.txt`, `*_full_pipeline_report.txt`, `*_final_report_classified.csv`.

Critères de succès:

- Pipeline OK sans erreurs fatales.
- Variance expliquée/justifiée par au moins 1–2 bridges.

### Phase 3 — Élargissement (0,5–1 jour)

Objectif: robustesse et généralisation.

- Ajouter 1–2 IPE supplémentaires (formats variés si possible).
- Ajuster/étendre les règles Bridges si nécessaire.
- Lancer les tests de fumée et 1–2 tests ciblés (classification).

### Phase 4 — Packaging POC (0,5 jour)

Objectif: rendre la démonstration partageable et audit-ready.

- Regrouper outputs dans `evidence/<horodatage>/` avec un README succinct.
- Ajouter un court memo des résultats et limites connues.
- Lister les quick-wins/next steps.

---

## 3) KPIs & critères de succès

- Taux de lignes classifiées (bridges) sur chaque IPE.
- Variance résiduelle vs GL après classification.
- Temps d’exécution bout-en-bout (< X min en démo, < Y min en réel).
- Reproductibilité (mêmes artefacts sur relance, hash/horodatage, logs complets).

---

## 4) Risques & mitigations

- Accès cloud retardé: prévoir un mode « offline » (Phase 0) + IPE local en Phase 2.
- Qualité de données hétérogène: commencer avec 1 IPE bien compris, fixer le mapping tôt.
- Secrets/SSO: stocker hors repo (`data/credentials/`, variables d’env), docs OKTA à jour.
- Volumétrie: échantillonner en POC, valider limites (timeout Athena, mémoire locale).

---

## 5) À décider côté métier/IT (inputs attendus)

- Liste des IPE pilotes (fichier, source, propriétaire, taille, période, entité/pays).
- Indicateur de la source GL de référence (ou GL démo si non prêt).
- Règles spécifiques de classification/justification (si différentes du catalogue par défaut).
- Fenêtre temporelle (périodes) et métriques qui feront foi pour le go/no-go.

---

## 6) Livrables fin de POC

- Dossier `evidence/<horodatage>/` complet + README.
- `*_final_report_classified.csv` consolidé et annoté.
- Mémo de résultats (écarts clés, bridges appliqués, reste à faire).
- Journal d’exécution (logs) et paramètres d’environnement (non secrets).

---

Références utiles:

- `docs/development/TESTING_GUIDE.md`, `docs/development/RUNNING_EXTRACTIONS.md`
- `src/bridges/catalog.py`, `src/bridges/classifier.py`
- Scripts: `scripts/run_demo.py`, `scripts/run_full_reconciliation.py`
