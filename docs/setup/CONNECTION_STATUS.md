# AWS Connection Status - Jumia SOX Project

**Date**: 16 Octobre 2025  
**Utilisateur**: gustavevernayavisia  
**Compte AWS**: 007809111365 (jumia-data-prod-datalake)

---

## ✅ Statut de la Connexion

### AWS Identity
```
UserId: AROAQDULVSVCYXJL6CHFG:gustavevernayavisia
Account: 007809111365
Arn: arn:aws:sts::007809111365:assumed-role/AWSReservedSSO_Data-Prod-DataAnalyst-NonFinance_190aef6284ce5b68/gustavevernayavisia
```

### Profil AWS Configuré
```bash
Profile Name: 007809111365_Data-Prod-DataAnalyst-NonFinance
Region: eu-west-1
Role: AWSReservedSSO_Data-Prod-DataAnalyst-NonFinance_190aef6284ce5b68
```

---

## 🔑 Permissions Disponibles

### ✅ Services Accessibles
- **S3**: ✅ Accès complet
  - Liste des buckets: OK
  - Lecture/Écriture: OK (à vérifier par bucket)

### ❌ Services Non Accessibles (Permissions manquantes)
- **Secrets Manager**: ❌ Accès refusé
  - Vous n'avez pas les permissions pour lire les secrets
  - Alternative: Utiliser les credentials directement ou demander les permissions

### 🔍 À Vérifier
- **Athena**: Permissions non testées
- **Redshift**: Permissions non testées

---

## 📋 Configuration Actuelle

### Fichier .env
```bash
AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
AWS_REGION=eu-west-1
USE_OKTA_AUTH=false
CUTOFF_DATE=2024-12-31
S3_BUCKET_EVIDENCE=jumia-sox-evidence
S3_BUCKET_DATA=jumia-sox-data-lake
```

### Fichier ~/.aws/credentials
```ini
[007809111365_Data-Prod-DataAnalyst-NonFinance]
aws_access_key_id=ASIA... (credentials temporaires)
aws_secret_access_key=...
aws_session_token=... (expire après quelques heures)
```

---

## 🚀 Utilisation

### Commandes de Base

```bash
# Définir le profil
export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance

# Vérifier l'identité
aws sts get-caller-identity

# Lister les buckets S3
aws s3 ls

# Lister le contenu d'un bucket spécifique
aws s3 ls s3://nom-du-bucket/

# Télécharger un fichier
aws s3 cp s3://bucket/fichier.txt ./

# Uploader un fichier
aws s3 cp ./fichier.txt s3://bucket/
```

### Utilisation en Python

```python
import boto3
import os

# Définir le profil
os.environ['AWS_PROFILE'] = '007809111365_Data-Prod-DataAnalyst-NonFinance'

# Créer un client S3
s3_client = boto3.client('s3', region_name='eu-west-1')

# Lister les buckets
response = s3_client.list_buckets()
for bucket in response['Buckets']:
    print(bucket['Name'])
```

---

## ⚠️ Limitations Actuelles

### 1. Credentials Temporaires
- **Durée de vie**: Les credentials expirent après quelques heures (généralement 12h)
- **Renouvellement**: Vous devrez récupérer de nouveaux credentials depuis:
  https://jumia.awsapps.com/start → Votre compte → "Command line or programmatic access"

### 2. Permissions Manquantes
- **Secrets Manager**: Vous ne pouvez pas accéder aux secrets AWS
  - **Impact**: Impossible de récupérer automatiquement les chaînes de connexion DB
  - **Solution**: 
    - Option 1: Demander les permissions Secrets Manager à votre admin AWS
    - Option 2: Utiliser les credentials DB directement dans votre code (moins sécurisé)
    - Option 3: Stocker les credentials dans des variables d'environnement

### 3. AWS SSO Login
- L'authentification via `aws sso login` ne fonctionne pas correctement
- **Solution actuelle**: Utiliser les credentials temporaires manuellement depuis le portail web

---

## 🔄 Renouveler les Credentials

Quand vos credentials expirent (erreur "ExpiredToken" ou "InvalidToken"):

1. **Aller sur**: https://jumia.awsapps.com/start
2. **Se connecter** avec Okta
3. **Cliquer sur votre compte** AWS (007809111365)
4. **Cliquer sur** "Command line or programmatic access"
5. **Copier** les credentials de l'Option 2
6. **Mettre à jour** `~/.aws/credentials`:

```bash
nano ~/.aws/credentials
# Remplacer les valeurs aws_access_key_id, aws_secret_access_key et aws_session_token
```

---

## 📚 Prochaines Étapes

### Immédiat
- [x] Connexion AWS établie
- [x] Accès S3 vérifié
- [ ] Tester l'accès Athena
- [ ] Vérifier quels buckets S3 sont accessibles pour le projet SOX

### À Faire
- [ ] Demander les permissions Secrets Manager si nécessaire
- [ ] Identifier les sources de données disponibles
- [ ] Tester une extraction IPE simple
- [ ] Configurer le code Python pour utiliser S3

### Permissions à Demander (Optionnel)
Si vous avez besoin d'accéder à Secrets Manager:
```
secretsmanager:GetSecretValue
secretsmanager:ListSecrets
```

---

## 🆘 Troubleshooting

### Erreur: "Unable to locate credentials"
```bash
export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
```

### Erreur: "ExpiredToken"
Renouvelez vos credentials depuis le portail web (voir section ci-dessus)

### Erreur: "Access Denied" sur S3
Vérifiez que vous utilisez le bon bucket. Tous les buckets ne sont pas forcément accessibles.

---

## 📞 Support

- **AWS Administrator**: Demander les permissions manquantes
- **Documentation**: 
  - Configuration complète: `docs/setup/OKTA_AWS_SETUP.md`
  - Quick Reference: `docs/setup/OKTA_QUICK_REFERENCE.md`
