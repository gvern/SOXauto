# SOXauto PG-01 🛡️# SOXauto PG-01 🛡️



**Enterprise-Grade SOX Automation for Financial Reconciliation****Enterprise-Grade SOX Automation for Financial Reconciliation**



[![POC In Progress](https://img.shields.io/badge/Status-POC%20In%20Progress-blue.svg)](https://github.com/gvern/SOXauto)[![POC In Progress](https://img.shields.io/badge/Status-POC%20In%20Progress-blue.svg)](https://github.com/gvern/SOXauto)

[![Goal: SOX Compliant](https://img.shields.io/badge/Goal-SOX%20Compliant-lightgrey.svg)](https://www.sox-online.com/)[![Goal: SOX Compliant](https://img.shields.io/badge/Goal-SOX%20Compliant-lightgrey.svg)](https://www.sox-online.com/)

[![Cloud Native](https://img.shields.io/badge/Cloud-AWS-orange.svg)](https://aws.amazon.com/)[![Cloud Native](https://img.shields.io/badge/Cloud-AWS-orange.svg)](https://aws.amazon.com/)

[![License](https://img.shields.io/badge/License-Enterprise-red.svg)](LICENSE)[![License](https://img.shields.io/badge/License-Enterprise-red.svg)](LICENSE)



> **Revolutionizing SOX compliance through intelligent automation and cryptographic evidence generation**> **Revolutionizing SOX compliance through intelligent automation and cryptographic evidence generation**



SOXauto PG-01 is an enterprise-grade automation system that transforms manual SOX reconciliation processes into secure, auditable, and scalable workflows. Built for financial institutions requiring bulletproof compliance and audit trails.SOXauto PG-01 is an enterprise-grade automation system that transforms manual SOX reconciliation processes into secure, auditable, and scalable workflows. Built for financial institutions requiring bulletproof compliance and audit trails.



------



## 🎯 **What Makes SOXauto Revolutionary**## 🎯 **What Makes SOXauto Revolutionary**



### Traditional Manual Process### Traditional Manual Process

- ❌ **15-30 minutes** per IPE extraction- ❌ **15-30 minutes** per IPE extraction

- ❌ **Screenshot evidence** (alterable, limited coverage)- ❌ **Screenshot evidence** (alterable, limited coverage)

- ❌ **Manual validation** (error-prone)- ❌ **Manual validation** (error-prone)

- ❌ **Scattered documentation** (audit nightmare)- ❌ **Scattered documentation** (audit nightmare)

- ❌ **Human errors** and inconsistencies- ❌ **Human errors** and inconsistencies



### SOXauto Automated Process### SOXauto Automated Process

- ✅ **2-3 minutes** per IPE extraction (90% faster)- ✅ **2-3 minutes** per IPE extraction (90% faster)

- ✅ **Cryptographic evidence** (tamper-proof, complete coverage)- ✅ **Cryptographic evidence** (tamper-proof, complete coverage)

- ✅ **Automated validation** (consistent, reliable)- ✅ **Automated validation** (consistent, reliable)

- ✅ **Structured audit packages** (enterprise-grade)- ✅ **Structured audit packages** (enterprise-grade)

- ✅ **Zero human errors** in execution- ✅ **Zero human errors** in execution



------



## 🏗️ **Architecture Overview**## 🏗️ **Architecture Overview**



```mermaid```mermaid

graph TDgraph TD

    subgraph "Phase 1: Data Structuring"    subgraph "Phase 1: Data Structuring"

        A[Scheduler] -- Triggers Monthly --> B[Orchestrator]        A[Scheduler] -- Triggers Monthly --> B[Orchestrator]

        B -- For each IPE --> C[IPE Runner]        B -- For each IPE --> C[IPE Runner]

        C -- Reads --> D{IPE Catalog}        C -- Reads --> D{IPE Config}

        C -- Gets credentials --> E[AWS Secrets/Okta]        C -- Gets credentials --> E[Secret Manager]

        C -- Extracts from --> F[AWS Athena / SQL Server]        C -- Extracts from --> F[Source Databases]

        C -- Performs --> G[Validation Engine]        C -- Performs --> G[Validation Engine]

        G -- Generates --> H[Digital Evidence Package]        G -- Generates --> H[Digital Evidence Package]

        G -- Writes to --> I[Amazon Athena]        G -- Writes to --> I[Amazon Athena]

    end    end



    subgraph "Phase 2 & 3: Analysis & Reporting"    subgraph "Phase 2 & 3: Analysis & Reporting"

        I -- All IPEs processed --> K[Reconciliation Agent]        I -- All IPEs processed --> K[Reconciliation Agent]

        K -- Calculates bridges --> L[Bridge Analysis]        K --> L[Classification Agent]

        L -- Generates --> M[PowerBI Dashboard]        L -- Generates --> M[Final Report]

        M -- Consumed by --> N[Auditors]        M -- Uploads to --> N[Google Drive/S3]

    end    end

    

    subgraph "Evidence Package Contents"    subgraph "Evidence Package Components"

        H --> P[Data Extract]        O[SQL Query] --> H

        H --> Q[Validation Results]        P[Data Snapshot] --> H

        H --> R[Execution Log]        Q[Crypto Hash] --> H

        H --> S[SHA-256 Hash]        R[Validation Results] --> H

    end        S[Execution Log] --> H

```    end

```

### Core Components

### Core Components

| Component | Role | Technology |

|-----------|------|------------|| Component | Role | Technology |

| **Orchestrator** | Main workflow engine | Python + Flask ||-----------|------|------------|

| **IPE Runner** | Individual IPE processor | Python + Pandas || **Orchestrator** | Main workflow engine | Python + Flask |

| **Evidence Manager** | SOX compliance engine | Cryptographic hashing || **IPE Runner** | Individual IPE processor | Python + Pandas |

| **AWS Utils** | Cloud service integration | AWS SDK (boto3) || **Evidence Manager** | SOX compliance engine | Cryptographic hashing |

| **Validation Engine** | Data quality assurance | Athena SQL + Statistical tests || **AWS Utils** | Cloud service integration | AWS SDK (boto3) |

| **Validation Engine** | Data quality assurance | Athena SQL + Statistical tests |

---

---

## 🚀 **Quick Start**

## 🚀 **Quick Start**

### Prerequisites

- Python 3.11+### Prerequisites

- Docker- Python 3.11+

- AWS CLI configured with SSO (Okta)- Docker

- SQL Server ODBC Driver (for legacy database access)- AWS CLI configured

- SQL Server ODBC Driver (for legacy database access)

### Local Development

```bash### Local Development

# Clone the repository```bash

git clone https://github.com/gvern/SOXauto.git# Clone the repository

cd SOXauto/PG-01git clone https://github.com/gvern/SOXauto.git

cd SOXauto

# Create and activate virtual environment

python3 -m venv .venv# Install dependencies

source .venv/bin/activatepip install -r requirements.txt



# Install dependencies# Set environment variables

pip install -r requirements.txtexport AWS_REGION="eu-west-1"

export CUTOFF_DATE="2024-05-01"

# Configure AWS credentials via Okta

bash scripts/update_aws_credentials.sh# Run IPE extraction (example)

python -m src.core.main

# Set environment variables

export AWS_PROFILE="007809111365_Data-Prod-DataAnalyst-NonFinance"# Run timing difference bridge analysis

export AWS_REGION="eu-west-1"python -m src.bridges.timing_difference

export CUTOFF_DATE="2025-09-30"```



# Run IPE extraction test### Docker Deployment

python3 tests/test_ipe_extraction_athena.py```bash

# Build the image

# Run timing difference bridge analysisdocker build -t soxauto-pg01 .

python -m src.bridges.timing_difference

```# Run the container

docker run -e AWS_REGION="eu-west-1" soxauto-pg01

### Docker Deployment```

```bash

# Build the image---

docker build -t soxauto-pg01 .

## 📦 **What's Inside**

# Run the container

docker run -e AWS_REGION="eu-west-1" \> **Professional Python package structure for scalability and production readiness**

  -e AWS_PROFILE="your-profile" \

  -v ~/.aws:/home/appuser/.aws:ro \```

  soxauto-pg01PG-01/

```├── 📁 src/                          # Source code (Python package)

│   ├── 📁 core/                     # Core application logic

---│   │   ├── 🐍 __init__.py          # Package initialization

│   │   ├── 📄 main.py              # Flask orchestrator (Cloud Run entry point)

## 📦 **Project Structure**│   │   ├── ⚙️ config.py             # IPE configurations (secure CTE patterns)

│   │   ├── 🏃 ipe_runner.py         # IPE execution engine

> **Professional Python package structure with clear separation of concerns**│   │   └── 🛡️ evidence_manager.py   # Digital evidence system (SHA-256)

│   ├── � bridges/                  # Bridge analysis scripts

```│   │   ├── 🐍 __init__.py          # Package initialization

PG-01/│   │   └── 📊 timing_difference.py  # Timing difference bridge automation

├── 📁 src/                          # Source code (Python package)│   ├── 📁 agents/                   # Future: Classification & reconciliation agents

│   ├── 📁 core/                     # Core application logic│   │   └── 🐍 __init__.py          # Package initialization

│   │   ├── 📁 catalog/              # IPE/CR catalog (single source of truth)│   └── 📁 utils/                    # Shared utilities

│   │   │   ├── 🐍 __init__.py│       ├── 🐍 __init__.py          # Package initialization

│   │   │   └── 📋 cpg1.py            # Unified C-PG-1 definitions│       └── 🔧 gcp_utils.py         # Google Cloud Platform abstractions

│   │   ├── 📁 runners/              # Execution engines│

│   │   │   ├── 🐍 __init__.py├── 📁 docs/                         # Comprehensive documentation

│   │   │   ├── 🏃 athena_runner.py  # AWS Athena queries│   ├── 📁 architecture/             # Architecture diagrams

│   │   │   └── 🏃 mssql_runner.py   # SQL Server (legacy)│   ├── 📁 deployment/               # Deployment guides

│   │   ├── 📁 evidence/             # SOX compliance│   │   ├── 🚀 deploy.md            # GCP production deployment

│   │   │   ├── 🐍 __init__.py│   │   └── ☁️ aws_migration.md     # AWS compatibility layer

│   │   │   └── 🛡️ manager.py        # Digital evidence (SHA-256)│   ├── 📁 development/              # Development documentation

│   │   ├── 📁 recon/                # Reconciliation logic│   │   ├── 📊 classification_matrix.md    # Business rules

│   │   │   ├── 🐍 __init__.py│   │   ├── 🤝 meeting_questions.md        # Stakeholder guide

│   │   │   └── 📊 cpg1.py           # CPG1 business rules│   │   ├── 📋 evidence_documentation.md   # Evidence system specs

│   │   └── 📄 main.py               # Flask orchestrator entry point│   │   └── 🔒 SECURITY_FIXES.md          # Security audit report

│   ├── 📁 bridges/                  # Bridge analysis scripts│   └── 📁 setup/                    # Setup instructions

│   │   ├── 🐍 __init__.py│       └── 📝 TIMING_DIFFERENCE_SETUP.md  # Bridge setup guide

│   │   └── 📊 timing_difference.py  # Timing difference automation│

│   ├── 📁 agents/                   # Future: AI agents├── 📁 scripts/                      # Automation scripts

│   │   └── 🐍 __init__.py│   ├── 🔧 quick_wins.sh            # Quick documentation setup

│   └── 📁 utils/                    # Shared utilities│   └── 🔄 restructure.sh           # Project restructuring script

│       ├── 🐍 __init__.py│

│       ├── ☁️ aws_utils.py           # AWS service abstractions├── 📁 data/                         # Data files (gitignored)

│       └── 🔐 okta_aws_auth.py      # Okta SSO integration│   ├── 📁 credentials/              # Service account credentials

││   └── 📁 outputs/                  # Bridge analysis outputs

├── 📁 docs/                         # Comprehensive documentation│

│   ├── 📁 architecture/             # System design├── 🐳 Dockerfile                   # Multi-stage production container

│   │   └── DATA_ARCHITECTURE.md├── ☁️ cloudbuild.yaml              # Google Cloud Build configuration

│   ├── 📁 deployment/               # Deployment guides├── 📋 requirements.txt             # Python dependencies

│   │   └── aws_deploy.md├── 🚫 .dockerignore               # Docker exclusions

│   ├── 📁 development/              # Development guides└── 🚫 .gitignore                  # Git exclusions (includes data/)

│   │   ├── TESTING_GUIDE.md```

│   │   ├── SECURITY_FIXES.md

│   │   └── evidence_documentation.md### Key Technologies

│   └── 📁 setup/                    # Setup instructions

│       ├── DATABASE_CONNECTION.md| Component | Technology | Purpose |

│       ├── OKTA_AWS_SETUP.md|-----------|-----------|---------|

│       └── OKTA_QUICK_REFERENCE.md| **Orchestration** | Python + Flask | Cloud Run web server for workflow coordination |

│| **Database Access** | pyodbc + pandas | Secure parameterized SQL execution |

├── 📁 scripts/                      # Automation scripts| **Cloud Platform** | GCP (Secret Manager, BigQuery, Drive) | Enterprise cloud services |

│   ├── 🔄 update_aws_credentials.sh # AWS credential refresh| **Evidence System** | hashlib (SHA-256) | Cryptographic integrity verification |

│   └── ✅ validate_ipe_config.py    # Config validation| **Bridge Analysis** | gspread + Google Sheets API | Automated reconciliation identification |

│| **Containerization** | Docker (multi-stage build) | Production-grade deployment |

├── 📁 tests/                        # Test suite

│   ├── ✅ test_athena_access.py---

│   ├── ✅ test_database_connection.py

│   └── ✅ test_ipe_extraction_athena.py## 🎮 **Digital Evidence System**

│

├── 📁 IPE_FILES/                    # IPE baseline files### Revolutionary Innovation

├── 📁 data/                         # Runtime data (gitignored)SOXauto generates **tamper-proof evidence packages** that surpass traditional screenshot methods:

│   ├── credentials/                 # AWS/Okta credentials

│   └── outputs/                     # Analysis outputs#### Traditional Evidence (Manual)

│```

├── 🐳 Dockerfile                   # Multi-stage production container📸 Screenshot.png

├── 📋 requirements.txt             # Python dependencies   - Shows ~20 rows

├── 🚫 .gitignore                  # Git exclusions   - Easily alterable

└── 📄 README.md                   # This file   - No integrity verification

```   - Limited audit value

```

### Key Technologies

#### SOXauto Evidence Package

| Component | Technology | Purpose |```

|-----------|-----------|---------|📦 IPE_07_20241015_143025_evidence.zip

| **Orchestration** | Python 3.11 + Flask | Web server for workflow coordination |├── 📄 01_executed_query.sql        # Exact query with parameters

| **Data Access** | awswrangler + pyodbc | AWS Athena and SQL Server |├── 📊 02_query_parameters.json     # Execution parameters

| **Cloud Platform** | AWS (Athena, S3, Secrets Manager, IAM) | Enterprise data lake |├── 📋 03_data_snapshot.csv         # Programmatic "screenshot"

| **Evidence System** | hashlib (SHA-256) | Cryptographic integrity verification |├── 📈 04_data_summary.json         # Statistical overview

| **Authentication** | Okta SSO + AWS STS | Enterprise identity management |├── 🔐 05_integrity_hash.json       # SHA-256 cryptographic proof

| **Containerization** | Docker (multi-stage build) | Production deployment |├── ✅ 06_validation_results.json   # SOX test results

└── 📜 07_execution_log.json        # Complete audit trail

---```



## 🎮 **Digital Evidence System**### Cryptographic Integrity

```python

### Revolutionary Cryptographic Integrity# Each dataset gets a unique SHA-256 hash

"hash_value": "a1b2c3d4e5f6789012345abcdef..."

Every IPE extraction generates a tamper-proof **Digital Evidence Package**:

# ANY alteration changes the hash completely

```jsonoriginal_hash  = "a1b2c3d4e5f6789012345abcdef..."

{altered_hash   = "9z8y7x6w5v4u3t2s1r0q9p8o7n6m..."

  "evidence_id": "IPE_07_20250930_143522_abc123",                  ↑ Completely different = Tamper detected

  "ipe_id": "IPE_07",```

  "cutoff_date": "2025-09-30",

  "extraction_timestamp": "2025-09-30T14:35:22.531Z",---

  "data_hash": "8f3d2a1c5b7e...4f9a",

  "row_count": 15847,## 🔧 **Configuration & Setup**

  "validation_status": "PASS",

  "critical_column_completeness": {### AWS Authentication with Okta SSO

    "customer_no": 100.0,

    "document_no": 100.0,SOXauto supports **Okta SSO authentication** for secure AWS access. This is the recommended method for production use.

    "posting_date": 100.0

  }#### Quick Setup

}```bash

```# 1. Install AWS CLI v2 (required for SSO)

brew install awscli  # macOS

### Package Contents# or download from https://aws.amazon.com/cli/



1. **Data Extract** (`ipe_data.csv`) - Raw query results# 2. Configure Okta profile (interactive)

2. **Evidence Metadata** (`evidence.json`) - Full audit trailpython3 scripts/setup_okta_profile.py

3. **Execution Log** (`execution.log`) - Detailed operation log

4. **SHA-256 Integrity Hash** - Cryptographic verification# 3. Login via Okta

aws sso login --profile jumia-sox-prod

This is **legally admissible** evidence for SOX audits.

# 4. Set environment variables

---export AWS_PROFILE=jumia-sox-prod

export USE_OKTA_AUTH=true

## 🔐 **Authentication & Security**export AWS_REGION=eu-west-1

```

### Okta SSO Integration

📚 **Detailed guide**: See [docs/setup/OKTA_AWS_SETUP.md](docs/setup/OKTA_AWS_SETUP.md)

SOXauto integrates with Okta for enterprise-grade authentication:

### Database Connection

```bash

# Quick credential refreshSOXauto supports **two authentication methods** for database access:

bash scripts/update_aws_credentials.sh

1. **AWS Secrets Manager** (Production) - Secure, managed credentials

# The script handles:2. **Environment Variable** (Development) - Direct connection string for testing

# 1. Okta SSO authentication

# 2. AWS STS token generation```bash

# 3. AWS credentials file update# Option 1: AWS Secrets Manager (requires permissions)

```# Credentials retrieved automatically from AWS Secrets Manager



### Security Best Practices# Option 2: Environment Variable Fallback

export DB_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server;DATABASE=NAV_BI;UID=user;PWD=pass;"

- ✅ **No hardcoded credentials** - All secrets via AWS Secrets Manager or Okta```

- ✅ **Parameterized queries** - SQL injection prevention

- ✅ **Least privilege IAM** - Minimal permissions📚 **Database setup guide**: See [docs/setup/DATABASE_CONNECTION.md](docs/setup/DATABASE_CONNECTION.md)

- ✅ **Cryptographic hashing** - Evidence integrity

- ✅ **Docker non-root user** - Container security### Environment Variables

```bash

See `docs/development/SECURITY_FIXES.md` for security audit details.# AWS Okta Configuration

export USE_OKTA_AUTH=true

---export AWS_PROFILE=jumia-sox-prod

export AWS_REGION=eu-west-1

## 📊 **IPE Catalog**

# Execution Parameters

SOXauto manages 10+ C-PG-1 IPEs and Control Reports:export CUTOFF_DATE=2024-12-31  # Optional, defaults to current month



| IPE ID | Title | Data Source | Status |# Database Connection (Optional - fallback if Secrets Manager unavailable)

|--------|-------|-------------|--------|export DB_CONNECTION_STRING="DRIVER={...};SERVER=...;DATABASE=...;"

| **IPE_07** | Customer balances - Monthly balances at date | NAV BI | ✅ Complete |```

| **IPE_08** | Store credit vouchers TV | BOB | ✅ Complete |

| **IPE_09** | BOB Sales Orders | BOB | ✅ Complete |You can also use a `.env` file (copy from `.env.example`):

| **IPE_10** | Customer prepayments TV | OMS | ⏳ Pending Athena mapping |```bash

| **IPE_11** | Seller Center Liability reconciliation | Seller Center/NAV | ✅ Complete |cp .env.example .env

| **IPE_12** | TV - Packages delivered not reconciled | OMS | ⏳ Pending Athena mapping |# Edit .env with your settings

| **IPE_31** | PG detailed TV extraction | OMS | ⏳ Pending Athena mapping |```

| **IPE_34** | Marketplace refund liability | OMS | ⏳ Pending Athena mapping |

| **CR_01** | Reconciliation: SC - NAV | Multiple | ✅ Complete |### Required Secrets (AWS Secrets Manager)

| **DOC_001** | IPE Catalog Master | N/A | ✅ Complete |```bash

# Database connection string

All IPE definitions live in `src/core/catalog/cpg1.py` - the single source of truth.aws secretsmanager create-secret \

  --name DB_CREDENTIALS_NAV_BI \

---  --secret-string file://connection_string.txt \

  --region eu-west-1 \

## 🧪 **Testing**  --profile jumia-sox-prod



### Run Tests# AWS credentials are managed via IAM roles in production

# For local development, use Okta SSO (recommended) or AWS CLI configuration

```bash```

# Full test suite

pytest tests/### IPE Configuration

IPEs are configured in `src/core/config.py` using a **secure CTE (Common Table Expression) pattern** to prevent SQL injection:

# Specific tests

python3 tests/test_athena_access.py```python

python3 tests/test_ipe_extraction_athena.pyIPE_CONFIGS = [

python3 tests/test_database_connection.py    {

        "id": "IPE_07",

# Validate IPE configuration        "description": "Customer ledger entries reconciliation",

python3 scripts/validate_ipe_config.py        "secret_name": "DB_CREDENTIALS_NAV_BI",

```        "main_query": """

            SELECT ... FROM [Customer Ledger Entry] WHERE [Posting Date] < ?

### Test Coverage        """,

        "validation": {

- ✅ AWS Athena connectivity            # Security: All validation queries use self-contained CTEs

- ✅ SQL Server connectivity (legacy)            "completeness_query": """

- ✅ IPE extraction workflow                WITH main_data AS (

- ✅ Evidence generation                    -- Full query with parameterized placeholders

- ✅ Validation engine                    SELECT ... WHERE [Posting Date] < ?

- ✅ Okta authentication                )

                SELECT COUNT(*) FROM main_data

---            """,

            "accuracy_positive_query": """

## 📚 **Documentation**                WITH main_data AS (...)

                SELECT COUNT(*) FROM main_data WHERE witness_id = 239726184

Comprehensive documentation available in `docs/`:            """,

            "accuracy_negative_query": """

### Setup Guides                WITH main_data AS (...)

- **[OKTA_AWS_SETUP.md](docs/setup/OKTA_AWS_SETUP.md)** - Complete Okta SSO configuration                SELECT COUNT(*) FROM main_data WHERE [Document No_] = 'EXCLUDED'

- **[DATABASE_CONNECTION.md](docs/setup/DATABASE_CONNECTION.md)** - Database connectivity guide            """

- **[OKTA_QUICK_REFERENCE.md](docs/setup/OKTA_QUICK_REFERENCE.md)** - Quick credential refresh        }

    }

### Architecture]

- **[DATA_ARCHITECTURE.md](docs/architecture/DATA_ARCHITECTURE.md)** - Data lake architecture```



### Development**Security Note**: All queries use parameterized `?` placeholders and CTE patterns to eliminate SQL injection risks.

- **[TESTING_GUIDE.md](docs/development/TESTING_GUIDE.md)** - Testing best practices

- **[SECURITY_FIXES.md](docs/development/SECURITY_FIXES.md)** - Security audit findings---

- **[evidence_documentation.md](docs/development/evidence_documentation.md)** - Evidence system specs

## 🎯 **SOX Validation Framework**

### Deployment

- **[aws_deploy.md](docs/deployment/aws_deploy.md)** - AWS ECS/Lambda deployment### Three-Tier Validation

Each IPE undergoes rigorous SOX compliance testing:

---

#### 1. Completeness Test

## 🚧 **Roadmap**```sql

-- Ensures all expected records are captured

### Phase 1: Foundation (Current)SELECT COUNT(*) FROM (main_extraction_query) 

- [x] Core IPE extraction engine-- Must match expected count from control query

- [x] Digital evidence system```

- [x] AWS Athena integration

- [x] Okta SSO authentication#### 2. Accuracy Test (Positive)

- [x] Unified IPE catalog```sql

- [ ] Complete Athena mappings for all IPEs-- Verifies witness transactions are included

SELECT COUNT(*) FROM (main_extraction_query) 

### Phase 2: Intelligence (Q1 2026)WHERE transaction_id = 'KNOWN_WITNESS_ID'

- [ ] AI-powered reconciliation agent-- Must return > 0

- [ ] Automatic bridge identification```

- [ ] Anomaly detection

- [ ] Natural language reports#### 3. Accuracy Test (Negative)

```sql

### Phase 3: Scale (Q2 2026)-- Confirms excluded transactions are not present

- [ ] Multi-entity supportSELECT COUNT(*) FROM (modified_extraction_query) 

- [ ] Real-time dashboardsWHERE transaction_id = 'KNOWN_EXCLUDED_ID'

- [ ] Advanced analytics-- Must return 0

- [ ] API for external systems```



---### Validation Results

```json

## 🤝 **Contributing**{

  "completeness": {"status": "PASS", "expected": 12547, "actual": 12547},

This is an enterprise internal project. For access or contributions:  "accuracy_positive": {"status": "PASS", "witness_count": 1},

  "accuracy_negative": {"status": "PASS", "excluded_count": 0},

1. **Authentication**: Ensure Okta SSO access  "overall_compliance": true

2. **AWS Permissions**: Request IAM role assignment}

3. **Development**: Follow the setup guide in `docs/setup/````

4. **Testing**: Run full test suite before commits

---

---

## 🚀 **Production Deployment**

## 📄 **License**

### Google Cloud Platform

Enterprise proprietary software. All rights reserved.

#### 1. Enable Required APIs

---```bash

gcloud services enable secretmanager.googleapis.com

## 🔗 **Resources**gcloud services enable bigquery.googleapis.com

gcloud services enable run.googleapis.com

- **AWS Athena**: [Documentation](https://docs.aws.amazon.com/athena/)gcloud services enable cloudbuild.googleapis.com

- **Okta SSO**: [Enterprise SSO Guide](https://www.okta.com/)```

- **SOX Compliance**: [SOX Online](https://www.sox-online.com/)

- **awswrangler**: [AWS Data Wrangler](https://aws-sdk-pandas.readthedocs.io/)#### 2. Deploy with Cloud Build

```bash

---# Submit build

gcloud builds submit --config cloudbuild.yaml

**Built with ❤️ for enterprise-grade SOX compliance**

# Verify deployment
curl https://your-cloud-run-url/health
```

#### 3. Schedule Monthly Execution
```bash
gcloud scheduler jobs create http sox-pg01-monthly \
    --schedule="0 9 1 * *" \
    --uri="https://your-service-url/" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"cutoff_date": null}'
```

### Amazon Web Services
SOXauto is fully compatible with AWS. See [`aws_migration.md`](aws_migration.md) for detailed migration guide.

---

## 🧪 **Testing & Validation**

### Run Evidence System Demo
```bash
python test_evidence_system.py
```

**Output:**
```
🧪 DÉMONSTRATION - Système d'Évidence Digitale SOX
============================================================
1️⃣ Initialisation du gestionnaire d'évidence...
   📁 Package créé: /tmp/evidence/DEMO_IPE/20241015_143025_123

2️⃣ Création du package d'évidence...
   📊 Données créées: 500 lignes, 8 colonnes

3️⃣ Génération des preuves d'évidence...
   ✅ Requête SQL sauvegardée
   ✅ Échantillon de données sauvegardé
   ✅ Hash d'intégrité généré: a1b2c3d4e5f6789...
   ✅ Résultats de validation sauvegardés

🎉 DÉMONSTRATION TERMINÉE
```

### Health Check
```bash
curl https://your-deployment-url/health
```

```json
{
  "status": "healthy",
  "service": "SOXauto-PG01",
  "timestamp": "2024-10-15T14:30:25.123456"
}
```

---

## 📊 **Monitoring & Observability**

### Key Metrics to Monitor

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Execution Time | > 10 minutes | Warning |
| Validation Failures | > 0 | Critical |
| Evidence Generation | Failed | Critical |
| Memory Usage | > 1.5GB | Warning |
| Error Rate | > 1% | Critical |

### Logging Structure
```json
{
  "timestamp": "2024-10-15T14:30:25.123456",
  "level": "INFO",
  "ipe_id": "IPE_07",
  "action": "VALIDATION_COMPLETED",
  "details": {
    "rows_processed": 12547,
    "validation_status": "PASS",
    "execution_time_ms": 2345
  }
}
```

### Dashboard Queries (BigQuery)
```sql
-- Daily execution summary
SELECT 
  DATE(extraction_timestamp) as execution_date,
  ipe_id,
  COUNT(*) as executions,
  SUM(CASE WHEN validation_status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
  AVG(execution_time_seconds) as avg_execution_time
FROM `project.dataset.audit_log`
WHERE DATE(extraction_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1, 2
ORDER BY 1 DESC, 2
```

---

## 🔐 **Security & Compliance**

### Security Features
- 🔐 **Secret Manager Integration** - No hardcoded credentials
- 🛡️ **Least Privilege IAM** - Minimal required permissions
- 🔒 **Data Encryption** - In transit and at rest
- 📜 **Audit Logging** - Complete activity trail
- 🏗️ **Container Security** - Non-root user, minimal attack surface

### SOX Compliance
- ✅ **Segregation of Duties** - Automated execution removes human bias
- ✅ **Data Integrity** - Cryptographic evidence prevents tampering
- ✅ **Audit Trail** - Complete documentation of all actions
- ✅ **Access Controls** - IAM-based permissions
- ✅ **Testing & Validation** - Automated control testing

### Required IAM Permissions
```json
{
  "roles": [
    "roles/secretmanager.secretAccessor",
    "roles/bigquery.dataEditor",
    "roles/storage.objectCreator",
    "roles/logging.logWriter"
  ]
}
```

---

## 🤝 **Contributing**

### Development Workflow
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards
- **Python**: Follow PEP 8
- **Documentation**: Comprehensive docstrings
- **Testing**: Unit tests for new features
- **Security**: No hardcoded secrets or credentials

### Business Logic Changes
For modifications to IPE configurations or validation rules:
1. Update classification matrix
2. Document business justification
3. Get stakeholder approval
4. Implement with comprehensive testing

---

## 📋 **API Reference**

### Endpoints

#### Health Check
```http
GET /health
```
```json
{
  "status": "healthy",
  "service": "SOXauto-PG01",
  "timestamp": "2024-10-15T14:30:25.123456"
}
```

#### Configuration
```http
GET /config
```
```json
{
  "project_id": "jumia-sox-project",
  "bigquery_dataset": "jumia_sox_reconciliation",
  "configured_ipes": [
    {"id": "IPE_07", "description": "Customer ledger entries"},
    {"id": "CR_03_04", "description": "GL entries"}
  ],
  "total_ipes": 2
}
```

#### Execute Workflow
```http
POST /
Content-Type: application/json

{
  "cutoff_date": "2024-05-01"
}
```
```json
{
  "workflow_id": "SOXauto_PG01_20241015_143025",
  "overall_status": "SUCCESS",
  "summary": {
    "total_ipes": 2,
    "successful_ipes": 2,
    "failed_ipes": 0,
    "total_rows_processed": 25094
  }
}
```

---

## 🆘 **Troubleshooting**

### Common Issues

#### Connection Errors
```bash
# Check secret accessibility
gcloud secrets versions access latest --secret="DB_CREDENTIALS_NAV_BI"

# Test connectivity
telnet your-sql-server 1433
```

#### Memory Issues
```bash
# Increase Cloud Run memory
gcloud run services update soxauto-pg01 --memory 4Gi
```

#### Validation Failures
```bash
# Check validation logs
gcloud logs read "resource.type=cloud_run_revision" \
  --filter="jsonPayload.ipe_id=IPE_07"
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python main.py
```

### Support Contacts
- **Technical Issues**: [Insert technical team contact]
- **Business Rules**: [Insert business stakeholder contact]
- **Infrastructure**: [Insert DevOps team contact]

---

## 📈 **Performance Targets**

### Expected Execution Times (Production)
| IPE | Manual Process | SOXauto Target | Expected Improvement |
|-----|---------------|----------------|---------------------|
| IPE_07 | 25 minutes | 2-3 minutes | 🚀 ~90% faster |
| CR_03_04 | 20 minutes | 2-3 minutes | 🚀 ~90% faster |
| IPE_12 | 30 minutes | 2-3 minutes | 🚀 ~90% faster |

### Target Resource Usage
- **Memory**: <2GB peak (optimized for Cloud Run)
- **CPU**: 1-2 cores during execution
- **Storage**: ~50MB evidence per IPE
- **Network**: ~10MB data transfer per execution

---

## 🏆 **Success Targets**

### Project Objectives
- ⏱️ **Time Savings Target**: 90% reduction in manual effort
- 🎯 **Accuracy Goal**: 99%+ automated validation success rate
- 🛡️ **Compliance Goal**: 100% audit-ready evidence packages
- 💰 **Cost Reduction Target**: 80%+ decrease in operational costs
- 📊 **Scalability Goal**: Handle 50+ IPEs without performance degradation

### Expected Business Impact
- **Risk Reduction**: Eliminate human errors in SOX processes
- **Audit Confidence**: Cryptographic evidence to satisfy external auditors
- **Operational Efficiency**: Redirect team focus to value-added analysis
- **Compliance Assurance**: Automated controls for consistent compliance

### POC Success Criteria
- ✅ **Phase 1**: Successful IPE data extraction and validation
- 🔄 **Phase 2**: Agent-based reconciliation and classification
- 📊 **Phase 3**: Automated report generation and delivery

---

## 📚 **Additional Resources**

### Documentation
- 📋 [Classification Matrix](classification_matrix.md) - Business rules and logic
- 🤝 [Meeting Questions](meeting_questions.md) - Stakeholder alignment guide
- 🚀 [Deployment Guide](deploy.md) - Production deployment instructions
- ☁️ [AWS Migration](aws_migration.md) - AWS compatibility and migration
- 🛡️ [Evidence System](evidence_documentation.md) - Digital evidence framework

### External Links
- [SOX Compliance Guidelines](https://www.sox-online.com/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [AWS Fargate Documentation](https://aws.amazon.com/fargate/)
- [Python Security Best Practices](https://python.org/dev/security/)

---

## 📄 **License**

This project is licensed under the Enterprise License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **Business Stakeholders** for domain expertise and validation
- **Audit Team** for compliance requirements and testing
- **Infrastructure Team** for cloud platform support
- **Security Team** for security architecture review

---

## 🎯 **Roadmap**

### Upcoming Features
- 🤖 **AI-Powered Anomaly Detection** - ML-based outlier identification
- 📊 **Real-time Dashboards** - Live monitoring and reporting
- 🔄 **Multi-tenant Support** - Support for multiple subsidiaries
- 📱 **Mobile Notifications** - Instant alerts for critical issues
- 🌐 **API Expansion** - RESTful APIs for external integrations

### Long-term Vision
Transform SOXauto into a comprehensive financial automation platform covering all SOX requirements across the organization.

---

**🎉 SOXauto PG-01: Where Compliance Meets Innovation**

*Built with ❤️ for enterprise-grade financial automation*