# SOXauto PG-01

## Enterprise-Grade SOX Automation for Financial Reconciliation

[![POC In Progress](https://img.shields.io/badge/Status-POC%20In%20Progress-blue.svg)](https://github.com/gvern/SOXauto)
[![Goal: SOX Compliant](https://img.shields.io/badge/Goal-SOX%20Compliant-lightgrey.svg)](https://www.sox-online.com/)
[![Cloud Native](https://img.shields.io/badge/Cloud-AWS-orange.svg)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-Enterprise-red.svg)](LICENSE)

> **Revolutionizing SOX compliance through intelligent automation and cryptographic evidence generation**

SOXauto PG-01 is an enterprise-grade automation system that transforms manual SOX reconciliation processes into secure, auditable, and scalable workflows. Built for financial institutions requiring bulletproof compliance and audit trails.

------

## What Makes SOXauto Revolutionary

### Traditional Manual Process

- **15-30 minutes** per IPE extraction
- **Screenshot evidence** (alterable, limited coverage)
- **Manual validation** (error-prone)
- **Scattered documentation** (audit nightmare)
- **Human errors** and inconsistencies

### SOXauto Automated Process

- **2-3 minutes** per IPE extraction (90% faster)
- **Cryptographic evidence** (tamper-proof, complete coverage)
- **Automated validation** (consistent, reliable)
- **Structured audit packages** (enterprise-grade)
- **Zero human errors** in execution

------

## Architecture Overview

```mermaid
graph TD
    subgraph "Phase 1: Data Structuring"
        A[Scheduler] -- Triggers Monthly --> B[Orchestrator]
        B -- For each IPE --> C[IPE Runner]
        C -- Reads --> D{IPE Catalog}
        C -- Gets credentials --> E[AWS Secrets/Okta]
        C -- Extracts from --> F[AWS Athena / SQL Server]
        C -- Performs --> G[Validation Engine]
        G -- Generates --> H[Digital Evidence Package]
        G -- Writes to --> I[Amazon Athena]
    end

    subgraph "Phase 2 & 3: Analysis & Reporting"
        I -- All IPEs processed --> K[Reconciliation Agent]
        K -- Calculates bridges --> L[Bridge Analysis]
        L -- Generates --> M[PowerBI Dashboard]
        M -- Consumed by --> N[Auditors]
    end
    
    subgraph "Evidence Package Contents"
        H --> O[SQL Query]
        H --> P[Data Snapshot]
        H --> Q[Crypto Hash]
        H --> R[Validation Results]
        H --> S[Execution Log]
    end
```

### Core Components

| Component | Role | Technology |
|-----------|------|------------|
| **Orchestrator** | Main workflow engine | Python + Flask |
| **IPE Runner** | Individual IPE processor | Python + Pandas |
| **Evidence Manager** | SOX compliance engine | Cryptographic hashing |
| **AWS Utils** | Cloud service integration | AWS SDK (boto3) |
| **Validation Engine** | Data quality assurance | Athena SQL + Statistical tests |

------

## The Complete SOXauto Workflow: From Auth to Evidence

The system is designed as a clear, linear pipeline. Understanding this workflow is key to seeing how all the pieces fit together.

### The High-Level Process

The entire operation can be visualized in five distinct stages:

### Authentication → Orchestration → Execution → Validation → Evidence Generation

Here’s a step-by-step breakdown:

#### 1. Authentication (Your Entry Point)

- **What happens**: You run your `update_aws_credentials.sh` script to obtain temporary, secure credentials from AWS via Okta.
- **Key Scripts**: `scripts/update_aws_credentials.sh`, `src/utils/okta_aws_auth.py`
- **Result**: A valid AWS session is created, allowing your scripts to interact with AWS services like Athena and S3.

#### 2. Orchestration (The "Workflow")

- **What happens**: The `execute_ipe_workflow` function in `workflow.py` kicks off the main process. It loops through all the IPEs defined in your catalog and runs them one by one.
- **Key Scripts**: `src/orchestrators/workflow.py`, `src/api/app.py` (which calls the workflow).
- **Result**: Each IPE is passed to the appropriate runner for execution.

#### 3. Execution (The "Runner")

- **What happens**: The `IPERunnerAthena` class takes an IPE definition from the catalog. It formats the Athena SQL query, replacing placeholders like `{cutoff_date}` with the correct values. It then uses the `awswrangler` library to execute this query against the Athena data lake.
- **Key Scripts**: `src/core/runners/athena_runner.py`, `src/core/catalog/cpg1.py`
- **Result**: A pandas DataFrame containing the raw data extract for that IPE.

#### 4. Validation (The "SOX Check")

- **What happens**: After the data is extracted, the `athena_runner` performs in-memory validation tests on the DataFrame based on the rules defined in the catalog (`critical_columns`, `accuracy_positive`, etc.).
- **Key Scripts**: `src/core/runners/athena_runner.py` (the `_validate_data` method).
- **Result**: A JSON object containing the PASS/FAIL status for each validation rule (Completeness, Accuracy).

#### 5. Evidence Generation (The "Audit Trail")

- **What happens**: Throughout the execution and validation process, the `DigitalEvidenceManager` is called to create a comprehensive, tamper-proof audit trail.
- **Key Scripts**: `src/core/evidence/manager.py`
- **Result**: A zipped evidence package containing the 7 critical files (the executed query, data snapshot, cryptographic hash, validation results, etc.) is saved to the `/evidence` directory.

------

## Quick Start

### Prerequisites

- Python 3.11+
- Docker
- AWS CLI configured
- SQL Server ODBC Driver (for legacy database access)

### Local Development

```bash
# Clone the repository
git clone https://github.com/gvern/SOXauto.git
cd SOXauto

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AWS_REGION="eu-west-1"
export CUTOFF_DATE="2024-05-01"

# Run IPE extraction (example)
python -m src.core.main

# Run timing difference bridge analysis
python -m src.bridges.timing_difference
```

### Docker Deployment

```bash
# Build the image
docker build -t soxauto-pg01 .

# Run the container
docker run -e AWS_REGION="eu-west-1" soxauto-pg01
```

------
## Project Structure

> **Professional Python package structure with clear separation of concerns**

```plaintext
PG-01/
├── src/                          # Source code (Python package)
│   ├── core/                     # Core application logic
│   │   ├── catalog/              # IPE/CR catalog (single source of truth)
│   │   │   ├── __init__.py
│   │   │   └── cpg1.py            # Unified C-PG-1 definitions
│   │   ├── runners/              # Execution engines
│   │   │   ├── __init__.py
│   │   │   ├── athena_runner.py  # AWS Athena queries
│   │   │   └── mssql_runner.py   # SQL Server (legacy)
│   │   ├── evidence/             # SOX compliance
│   │   │   ├── __init__.py
│   │   │   └── manager.py        # Digital evidence (SHA-256)
│   │   ├── recon/                # Reconciliation logic
│   │   │   ├── __init__.py
│   │   │   └── cpg1.py           # CPG1 business rules
│   │   └── main.py               # Flask orchestrator entry point
│   ├── bridges/                  # Bridge analysis scripts
│   │   ├── __init__.py
│   │   └── timing_difference.py  # Timing difference automation
│   ├── agents/                   # Future: AI agents
│   │   └── __init__.py
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       ├── aws_utils.py           # AWS service abstractions
│       └── okta_aws_auth.py      # Okta SSO integration
│
├── docs/                         # Comprehensive documentation
│   ├── architecture/             # System design
│   │   └── DATA_ARCHITECTURE.md
│   ├── deployment/               # Deployment guides
│   │   └── aws_deploy.md
│   ├── development/              # Development guides
│   │   ├── TESTING_GUIDE.md
│   │   ├── SECURITY_FIXES.md
│   │   └── evidence_documentation.md
│   └── setup/                    # Setup instructions
│       ├── DATABASE_CONNECTION.md
│       ├── OKTA_AWS_SETUP.md
│       └── OKTA_QUICK_REFERENCE.md
│
├── scripts/                      # Automation scripts
│   ├── update_aws_credentials.sh # AWS credential refresh
│   └── validate_ipe_config.py    # Config validation
│
├── tests/                        # Test suite
│   ├── test_athena_access.py
│   ├── test_database_connection.py
│   └── test_ipe_extraction_athena.py
│
├── IPE_FILES/                    # IPE baseline files
├── data/                         # Runtime data (gitignored)
│   ├── credentials/                 # AWS/Okta credentials
│   └── outputs/                     # Analysis outputs
│
├── Dockerfile                   # Multi-stage production container
├── requirements.txt             # Python dependencies
├── .gitignore                  # Git exclusions
└── README.md                   # This file
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | Python 3.11 + Flask | Web server for workflow coordination |
| **Data Access** | awswrangler + pyodbc | AWS Athena and SQL Server |
| **Cloud Platform** | AWS (Athena, S3, Secrets Manager, IAM) | Enterprise data lake |
| **Evidence System** | hashlib (SHA-256) | Cryptographic integrity verification |
| **Authentication** | Okta SSO + AWS STS | Enterprise identity management |
| **Containerization** | Docker (multi-stage build) | Production deployment |

------

## Digital Evidence System

Every IPE extraction generates a tamper-proof **Digital Evidence Package**:

```json
{
  "evidence_id": "IPE_07_20250930_143522_abc123",
  "ipe_id": "IPE_07",
  "cutoff_date": "2025-09-30",
  "extraction_timestamp": "2025-09-30T14:35:22.531Z",
  "data_hash": "8f3d2a1c5b7e...4f9a",
  "row_count": 15847,
  "validation_status": "PASS",
  "critical_column_completeness": {
    "customer_no": 100.0,
    "document_no": 100.0,
    "posting_date": 100.0
  }
}
```

### Package Contents

1. **Data Extract** (`ipe_data.csv`) - Raw query results
2. **Evidence Metadata** (`evidence.json`) - Full audit trail
3. **Execution Log** (`execution.log`) - Detailed operation log
4. **SHA-256 Integrity Hash** - Cryptographic verification

This is **legally admissible** evidence for SOX audits.

------
## Authentication & Security

### Okta SSO Integration

SOXauto integrates with Okta for enterprise-grade authentication:

```bash
# Quick credential refresh
bash scripts/update_aws_credentials.sh
# The script handles:
# 1. Okta SSO authentication
# 2. AWS STS token generation
# 3. AWS credentials file update
```

### Security Best Practices

- **No hardcoded credentials** - All secrets via AWS Secrets Manager or Okta
- **Parameterized queries** - SQL injection prevention
- **Least privilege IAM** - Minimal permissions
- **Cryptographic hashing** - Evidence integrity
- **Docker non-root user** - Container security

See `docs/development/SECURITY_FIXES.md` for security audit details.

------
## IPE Catalog

SOXauto manages 10+ C-PG-1 IPEs and Control Reports:

| IPE ID | Title | Data Source | Status |
|--------|-------|-------------|--------|
| **IPE_07** | Customer balances - Monthly balances at date | NAV BI | Complete |
| **IPE_08** | Store credit vouchers TV | BOB | Complete |
| **IPE_09** | BOB Sales Orders | BOB | Complete |
| **IPE_10** | Customer prepayments TV | OMS | Pending Athena mapping |
| **IPE_11** | Seller Center Liability reconciliation | Seller Center/NAV | Complete |
| **IPE_12** | TV - Packages delivered not reconciled | OMS | Pending Athena mapping |
| **IPE_31** | PG detailed TV extraction | OMS | Pending Athena mapping |
| **IPE_34** | Marketplace refund liability | OMS | Pending Athena mapping |
| **CR_01** | Reconciliation: SC - NAV | Multiple | Complete |
| **DOC_001** | IPE Catalog Master | N/A | Complete |

All IPE definitions live in `src/core/catalog/cpg1.py` - the single source of truth.

------
## Testing

### Run Tests

```bash
# Full test suite
pytest tests/

# Specific tests
python3 tests/test_athena_access.py
python3 tests/test_ipe_extraction_athena.py
python3 tests/test_database_connection.py

# Validate IPE configuration
python3 scripts/validate_ipe_config.py
```

### Test Coverage

- AWS Athena connectivity
- SQL Server connectivity (legacy)
- IPE extraction workflow
- Evidence generation
- Validation engine
- Okta authentication

------
## Documentation

Comprehensive documentation available in `docs/`:

### Setup Guides

- **[OKTA_AWS_SETUP.md](docs/setup/OKTA_AWS_SETUP.md)** - Complete Okta SSO configuration
- **[DATABASE_CONNECTION.md](docs/setup/DATABASE_CONNECTION.md)** - Database connectivity guide
- **[OKTA_QUICK_REFERENCE.md](docs/setup/OKTA_QUICK_REFERENCE.md)** - Quick credential refresh

### Architecture

- **[DATA_ARCHITECTURE.md](docs/architecture/DATA_ARCHITECTURE.md)** - Data lake architecture

### Development

- **[TESTING_GUIDE.md](docs/development/TESTING_GUIDE.md)** - Testing best practices
- **[SECURITY_FIXES.md](docs/development/SECURITY_FIXES.md)** - Security audit findings
- **[evidence_documentation.md](docs/development/evidence_documentation.md)** - Evidence system specs
- **[RUNNING_EXTRACTIONS.md](docs/development/RUNNING_EXTRACTIONS.md)** - Running extractions with SQL parameters

### Deployment

- **[aws_deploy.md](docs/deployment/aws_deploy.md)** - AWS ECS/Lambda deployment

------

## Roadmap

### Phase 1: Foundation (Current)

- [x] Core IPE extraction engine
- [x] Digital evidence system
- [x] AWS Athena integration
- [x] Okta SSO authentication
- [x] Unified IPE catalog
- [ ] Complete Athena mappings for all IPEs

### Phase 2: Intelligence (Q1 2026)

- [ ] AI-powered reconciliation agent
- [ ] Automatic bridge identification
- [ ] Anomaly detection
- [ ] Natural language reports

### Phase 3: Scale (Q2 2026)

- [ ] Multi-entity support
- [ ] Real-time dashboards
- [ ] Advanced analytics
- [ ] API for external systems

------

## Contributing

This is an enterprise internal project. For access or contributions:

1. **Authentication**: Ensure Okta SSO access
2. **AWS Permissions**: Request IAM role assignment
3. **Development**: Follow the setup guide in `docs/setup/`
4. **Testing**: Run full test suite before commits

------

## License

Enterprise proprietary software. All rights reserved.

------

## Resources

- **AWS Athena**: [Documentation](https://docs.aws.amazon.com/athena/)
- **Okta SSO**: [Enterprise SSO Guide](https://www.okta.com/)
- **SOX Compliance**: [SOX Online](https://www.sox-online.com/)
- **awswrangler**: [AWS Data Wrangler](https://aws-sdk-pandas.readthedocs.io/)

------

Built with love for enterprise-grade SOX compliance
