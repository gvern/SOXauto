# PROJECT DASHBOARD — SOXauto PG-01

> Source of truth for current priorities, status, and links. Updated: 2025-10-23

## Objectifs

- Phase 1 (prioritaire): Répliquer le processus manuel de réconciliation via MSSQL comme décrit dans `docs/development/TODO_MANUAL_PROCESS.md`.
- Phase 2 (cible): Migrer progressivement les IPEs éligibles vers l’architecture AWS Athena.

## Décisions récentes

- Utiliser un compte de service MSSQL en lecture seule pour un accès direct au Data Warehouse (pas d’ETL intermédiaire). Athena et l’ingestion redeviennent des cibles de phase 2.

## Statut d’avancement (IPEs)

| IPE | Description (résumé) | Source | Statut | Responsable |
|-----|-----------------------|--------|--------|-------------|
| IPE_07 | Customer balances (monthly balances) | MSSQL | À faire | - |
| IPE_09 | BOB Sales Orders | MSSQL | À faire | - |
| IPE_31 | PG detailed TV extraction | MSSQL | À faire | - |

Remarques:

- Les statuts ci-dessus décrivent la phase MSSQL de réplication du processus manuel. La cible Athena viendra ensuite.
- Mettre à jour à mesure des avancées (En cours, Bloqué, Fait) et ajouter le responsable.

## Bloqueurs actuels (top-1)

- En attente des identifiants du compte de service MSSQL (lecture seule). Dès réception: valider via `scripts/check_mssql_connection.py`.

## Liens clés

- Processus manuel à répliquer: `docs/development/TODO_MANUAL_PROCESS.md`
- Catalogue IPE (définitions): `src/core/catalog/cpg1.py`
- Dossiers d’évidence générés: `evidence/`
- Scripts de connectivité MSSQL: `scripts/check_mssql_connection.py`

## Prochaines actions (Phase 1)

1. Valider la connexion MSSQL (drivers ODBC, réseau/pare-feu, secrets, DSN/URI) via `scripts/check_mssql_connection.py`.
2. Centraliser les requêtes « vraies » dans `src/core/catalog/cpg1.py` avec `source: "mssql"`.
3. Exécuter les IPE via le runner MSSQL et produire les fichiers intermédiaires (CSV/Excel) comme dans `TODO_MANUAL_PROCESS.md`.
4. Brancher le Digital Evidence Manager dans le runner MSSQL et générer les 7 fichiers d’évidence.

## Notes

- Le README reste la vision cible. Ce tableau de bord reflète l’avancement opérationnel réel et doit être consulté en priorité.
- Merci d’archiver les documents obsolètes dans `docs/development/archive/` pour limiter le bruit documentaire.
