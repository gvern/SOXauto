# SOXauto PG-01 - Production Deployment

## Architecture de Production

Cette application a été restructurée pour un déploiement professionnel sur Google Cloud Platform avec les composants suivants :

### 📁 Structure du Projet

```
PG-01/
├── main.py              # Orchestrateur principal (compatible Cloud Run)
├── config.py            # Configuration GCP (sans secrets)
├── gcp_utils.py         # Module d'utilitaires Google Cloud
├── ipe_runner.py        # Classe d'exécution des IPEs
├── requirements.txt     # Dépendances Python
├── Dockerfile          # Image de conteneur
├── .dockerignore       # Exclusions Docker
├── .gitignore          # Exclusions Git
└── deploy.md           # Ce guide de déploiement
```

### 🚀 Étapes de Déploiement

#### 1. Préparation de l'environnement GCP

```bash
# Configurer le projet GCP
export PROJECT_ID="votre-projet-gcp"
gcloud config set project $PROJECT_ID

# Activer les APIs nécessaires
gcloud services enable secretmanager.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
```

#### 2. Configuration des secrets

```bash
# Créer les secrets dans Secret Manager
gcloud secrets create DB_CREDENTIALS_NAV_BI --data-file=db_connection_string.txt
gcloud secrets create GOOGLE_SERVICE_ACCOUNT_CREDENTIALS --data-file=service-account.json

# Vérifier les secrets
gcloud secrets list
```

#### 3. Préparation de BigQuery

```bash
# Créer le dataset BigQuery
bq mk --dataset $PROJECT_ID:jumia_sox_reconciliation

# Optionnel: Créer les tables avec schéma prédéfini
bq mk --table $PROJECT_ID:jumia_sox_reconciliation.pg01_validated_ipe_ipe_07
```

#### 4. Construction et déploiement de l'image

```bash
# Construire l'image avec Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/soxauto-pg01

# Déployer sur Cloud Run
gcloud run deploy soxauto-pg01 \
    --image gcr.io/$PROJECT_ID/soxauto-pg01 \
    --platform managed \
    --region europe-west1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID
```

#### 5. Configuration de la planification

```bash
# Créer un job Cloud Scheduler pour exécution mensuelle
gcloud scheduler jobs create http sox-pg01-monthly \
    --schedule="0 9 1 * *" \
    --uri="https://soxauto-pg01-xxxx-ew.a.run.app/" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"cutoff_date": null}' \
    --time-zone="Europe/Paris"
```

### ⚙️ Configuration

#### Variables d'environnement nécessaires

```bash
# Dans config.py, mettre à jour :
GCP_PROJECT_ID = "votre-projet-gcp-reel"
BIGQUERY_DATASET = "jumia_sox_reconciliation"
GOOGLE_DRIVE_FOLDER_ID = "id_dossier_google_drive"
```

#### Secrets requis dans Secret Manager

1. **DB_CREDENTIALS_NAV_BI** : Chaîne de connexion SQL Server
   ```
   DRIVER={ODBC Driver 18 for SQL Server};SERVER=server.com;DATABASE=AIG_Nav_DW;UID=username;PWD=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
   ```

2. **GOOGLE_SERVICE_ACCOUNT_CREDENTIALS** : Clés JSON du service account
   ```json
   {
     "type": "service_account",
     "project_id": "votre-projet",
     "private_key_id": "...",
     "private_key": "...",
     "client_email": "service-account@projet.iam.gserviceaccount.com",
     ...
   }
   ```

### 📊 Monitoring et Alertes

#### Points de surveillance

1. **Health checks** : `GET /health`
2. **Configuration** : `GET /config`
3. **Logs Cloud Run** : Surveiller les erreurs et performances
4. **Métriques BigQuery** : Volume de données traitées

#### Alertes recommandées

```bash
# Alertes sur les échecs de workflow
gcloud alpha monitoring policies create --policy-from-file=alerting-policy.json
```

### 🧪 Tests

#### Test local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Exécuter localement (nécessite les variables d'environnement)
python main.py "2024-05-01"
```

#### Test de l'endpoint Cloud Run

```bash
# Test de santé
curl https://your-cloud-run-url/health

# Test d'exécution
curl -X POST https://your-cloud-run-url/ \
  -H "Content-Type: application/json" \
  -d '{"cutoff_date": "2024-05-01"}'
```

### 🔒 Sécurité

#### Permissions IAM minimales requises

```bash
# Pour le service account Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:cloud-run-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"
```

#### Bonnes pratiques

- ✅ Utilisation de Secret Manager pour tous les credentials
- ✅ Image Docker multi-stage pour optimiser la taille
- ✅ Utilisateur non-root dans le conteneur
- ✅ Health checks configurés
- ✅ Limitation des ressources Cloud Run
- ✅ Logs structurés pour le monitoring

### 📈 Performances

#### Optimisations appliquées

- **Connexions DB** : Pool de connexions avec gestion des timeouts
- **BigQuery** : Écriture par batch avec métadonnées de traçabilité
- **Mémoire** : Traitement streaming pour les gros volumes
- **Retry logic** : Gestion des erreurs transitoires

#### Scaling

- **Instances Cloud Run** : Max 10 instances pour gérer la charge
- **Timeout** : 60 minutes pour les traitements longs
- **Ressources** : 2 CPU, 2GB RAM par instance

### 🆘 Dépannage

#### Erreurs communes

1. **Échec de connexion DB** : Vérifier les secrets et la connectivité réseau
2. **Timeout BigQuery** : Augmenter les timeouts ou optimiser les requêtes
3. **Erreur de permissions** : Vérifier les rôles IAM du service account
4. **Out of memory** : Augmenter la mémoire Cloud Run ou optimiser le code

#### Logs utiles

```bash
# Logs Cloud Run
gcloud logs read "resource.type=cloud_run_revision" --limit=50

# Logs d'audit BigQuery
gcloud logs read "protoPayload.serviceName=bigquery.googleapis.com" --limit=20
```

### 📞 Support

En cas de problème, consulter :
- Logs Cloud Run dans la console GCP
- Métriques de performance dans Cloud Monitoring
- Statut des services GCP : https://status.cloud.google.com

---

**Version:** 2.0 Production Ready  
**Dernière mise à jour:** $(date)  
**Auteur:** Équipe SOX Automation