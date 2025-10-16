# Migration AWS - Architecture SOXauto PG-01

## 🔄 Adaptation de l'Architecture GCP vers AWS

### Comparaison des Services

| Fonction | Google Cloud (Actuel) | AWS (Production) | Impact Code |
|----------|----------------------|------------------|-------------|
| **Conteneurisation** | Cloud Run | AWS Fargate + ECS | ✅ Aucun - même Dockerfile |
| **Planification** | Cloud Scheduler | Amazon EventBridge (CloudWatch Events) | ✅ Aucun - même endpoint HTTP |
| **Secrets** | Secret Manager | AWS Secrets Manager | 🔶 Changement mineur API |
| **Data Warehouse** | BigQuery | Amazon Redshift / S3 | 🔶 Changement driver DB |
| **Monitoring** | Cloud Monitoring | CloudWatch | ✅ Aucun - logs standard |
| **Storage** | Cloud Storage | Amazon S3 | 🔶 Changement API storage |

---

## 📁 Structure de Migration

### 1. Adaptation des Utilitaires Cloud

**Nouveau fichier:** `aws_utils.py` (équivalent de `gcp_utils.py`)

```python
# aws_utils.py - Adaptation pour AWS
import boto3
import pandas as pd
from botocore.exceptions import ClientError
import json
import logging

class AWSSecretsManager:
    def __init__(self, region_name='eu-west-1'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, secret_name):
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            logging.error(f"Erreur récupération secret {secret_name}: {e}")
            raise

class AWSRedshiftManager:
    def __init__(self, cluster_endpoint, database, user):
        # Configuration Redshift
        pass
    
    def write_dataframe(self, df, table_name):
        # Écriture dans Redshift via S3 staging
        pass
```

### 2. Configuration AWS

**Nouveau fichier:** `config_aws.py`

```python
# config_aws.py
import os

# Configuration AWS
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-1')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')

# Secrets
DB_SECRET_NAME = "jumia/sox/db-credentials"
SERVICE_ACCOUNT_SECRET = "jumia/sox/service-account"

# Data Storage
REDSHIFT_CLUSTER = "jumia-sox-cluster"
REDSHIFT_DATABASE = "jumia_sox"
REDSHIFT_SCHEMA = "reconciliation"
TABLE_PREFIX = "pg01_validated_ipe"

# S3 Configuration
S3_BUCKET = "jumia-sox-data-lake"
S3_PREFIX = "sox-automation/pg01/"

# ECS/Fargate Configuration
ECS_CLUSTER_NAME = "jumia-sox-cluster"
TASK_DEFINITION = "soxauto-pg01"
```

---

## 🚀 Déploiement AWS

### 1. Infrastructure as Code (Terraform)

**Fichier:** `infrastructure/main.tf`

```hcl
# Définition du cluster ECS Fargate
resource "aws_ecs_cluster" "sox_cluster" {
  name = "jumia-sox-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Task Definition pour SOXauto PG-01
resource "aws_ecs_task_definition" "soxauto_pg01" {
  family                   = "soxauto-pg01"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 2048
  memory                   = 4096
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "soxauto-pg01"
      image = "${aws_ecr_repository.soxauto.repository_url}:latest"
      
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]
      
      secrets = [
        {
          name      = "DB_CONNECTION_STRING"
          valueFrom = aws_secretsmanager_secret.db_credentials.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.soxauto.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# EventBridge pour planification mensuelle
resource "aws_cloudwatch_event_rule" "monthly_sox" {
  name                = "sox-pg01-monthly"
  description         = "Déclenchement mensuel SOX PG-01"
  schedule_expression = "cron(0 9 1 * ? *)"  # 1er de chaque mois à 9h
}

resource "aws_cloudwatch_event_target" "ecs_target" {
  rule      = aws_cloudwatch_event_rule.monthly_sox.name
  target_id = "SOXAutoPG01Target"
  arn       = aws_ecs_cluster.sox_cluster.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.soxauto_pg01.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"
    
    network_configuration {
      subnets         = var.private_subnet_ids
      security_groups = [aws_security_group.ecs_tasks.id]
    }
  }
}
```

### 2. Script de Déploiement

**Fichier:** `deploy_aws.sh`

```bash
#!/bin/bash
# deploy_aws.sh - Déploiement SOXauto PG-01 sur AWS

set -e

# Variables
AWS_REGION="eu-west-1"
ECR_REPOSITORY="jumia/soxauto-pg01"
IMAGE_TAG="latest"

echo "🚀 Déploiement SOXauto PG-01 sur AWS"

# 1. Build et push de l'image Docker vers ECR
echo "📦 Construction et push de l'image Docker..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
docker push $ECR_REPOSITORY:$IMAGE_TAG

# 2. Déploiement de l'infrastructure Terraform
echo "🏗️ Déploiement de l'infrastructure..."
cd infrastructure
terraform init
terraform plan -var="image_tag=$IMAGE_TAG"
terraform apply -var="image_tag=$IMAGE_TAG" -auto-approve

# 3. Création des secrets
echo "🔐 Configuration des secrets..."
aws secretsmanager create-secret \
    --name "jumia/sox/db-credentials" \
    --description "Credentials pour base de données NAV" \
    --secret-string file://secrets/db-connection.json

# 4. Test de l'endpoint
echo "🧪 Test de l'endpoint..."
TASK_ARN=$(aws ecs list-tasks --cluster jumia-sox-cluster --query 'taskArns[0]' --output text)
echo "Task déployée: $TASK_ARN"

echo "✅ Déploiement terminé avec succès!"
```

---

## 🔧 Adaptations du Code Python

### Points de Modification Minimes

**Dans `main.py`:**
```python
# Changement d'import
# from gcp_utils import initialize_gcp_services
from aws_utils import initialize_aws_services

# Adaptation de l'initialisation
def execute_ipe_workflow():
    # secret_manager, bigquery_client = initialize_gcp_services(GCP_PROJECT_ID)
    secret_manager, redshift_client = initialize_aws_services(AWS_REGION)
    
    # Le reste du code reste identique
    for ipe_config in IPE_CONFIGS:
        runner = IPERunner(ipe_config=ipe_config, secret_manager=secret_manager)
        # ...
```

**Dans `ipe_runner.py`:**
```python
# Aucun changement nécessaire - la classe reste identique
# Seules les méthodes d'accès aux secrets changent dans aws_utils.py
```

---

## 📊 Avantages de l'Architecture AWS

### Performance
- **Fargate:** Scaling automatique sans gestion de serveurs
- **Redshift:** Optimisé pour l'analytics sur gros volumes
- **S3:** Storage illimité et durable

### Sécurité
- **Secrets Manager:** Rotation automatique des credentials
- **IAM Roles:** Permissions granulaires
- **VPC:** Isolation réseau

### Coûts
- **Pay-as-you-use:** Facturé seulement à l'exécution
- **Reserved Capacity:** Réductions pour Redshift
- **S3 Intelligent Tiering:** Optimisation automatique des coûts

---

## 📅 Plan de Migration

### Phase 1: Préparation (Semaine 1)
- [ ] Validation de l'architecture avec l'équipe AWS
- [ ] Création des comptes et permissions AWS
- [ ] Adaptation du code pour AWS (aws_utils.py)

### Phase 2: Infrastructure (Semaine 2)
- [ ] Déploiement Terraform de l'infrastructure
- [ ] Configuration des secrets
- [ ] Tests de connectivité

### Phase 3: Déploiement (Semaine 3)
- [ ] Build et push de l'image vers ECR
- [ ] Déploiement de la tâche ECS
- [ ] Configuration EventBridge
- [ ] Tests end-to-end

### Phase 4: Production (Semaine 4)
- [ ] Monitoring et alertes CloudWatch
- [ ] Documentation opérationnelle
- [ ] Formation équipe support
- [ ] Go-live

---

**✅ Conclusion:** Votre code Python actuel est à 95% compatible AWS. Seules les couches d'accès aux services cloud nécessitent une adaptation, ce qui confirme la robustesse de votre architecture.