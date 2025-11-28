# Copilot Instructions for SOXauto PG-01

## Project Overview

SOXauto PG-01 is an enterprise-grade SOX compliance automation system for financial reconciliation. The system extracts IPE (Information Produced by the Entity) data from on-premises SQL Server via Teleport tunnels, performs validation, and generates cryptographic digital evidence packages for audit compliance.

### Key Architecture Points

- **Orchestration**: Temporal.io Workflows (`src/orchestrators/`)
- **Database Connection**: Secure Teleport (`tsh`) tunnel to `fin-sql.jumia.local`
- **Data Processing**: Python with pandas for IPE extraction
- **Evidence System**: SHA-256 cryptographic hashing for tamper-proof audit trails
- **IPE Catalog**: Single source of truth in `src/core/catalog/cpg1.py`

## Tech Stack

- **Python 3.11+**
- **Temporal.io** for workflow orchestration
- **pandas/numpy** for data processing
- **pyodbc** for SQL Server connectivity
- **pytest** for testing
- **Docker** for containerization
- **Streamlit** for frontend UI

## Project Structure

```
src/
├── core/           # Core application logic
│   ├── catalog/    # IPE/CR catalog definitions
│   ├── runners/    # Execution engines (mssql_runner.py)
│   ├── evidence/   # Digital evidence generation
│   └── recon/      # Reconciliation logic
├── orchestrators/  # Temporal workflows and activities
├── bridges/        # Bridge analysis scripts
├── agents/         # AI agents (future)
├── api/            # API endpoints
├── frontend/       # Streamlit UI
└── utils/          # Shared utilities
```

## Coding Conventions

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Use descriptive variable and function names
- Keep functions focused and single-purpose
- Use f-strings for string formatting

### Code Organization

- Place new IPE definitions in `src/core/catalog/cpg1.py`
- Database operations should use `src/core/runners/mssql_runner.py`
- Evidence generation should use `src/core/evidence/manager.py`
- Temporal workflows belong in `src/orchestrators/`

### Documentation

- Document all public functions with docstrings
- Update `README.md` when adding significant features
- Keep `PROJECT_DASHBOARD.md` updated for project status

## Build and Test

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Running Tests

```bash
# Run smoke tests (default)
pytest tests/

# Run specific test file
pytest tests/test_smoke_core_modules.py -v

# Run with coverage
pytest tests/ --cov=src
```

### Linting

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/
```

### Demo Run

```bash
# Run offline demo with sample data
python3 scripts/run_demo.py --ipe IPE_07
```

## Security Guidelines

### Critical Security Requirements

- **Never hardcode credentials** - All database connections use Teleport
- **Use parameterized queries** - Prevent SQL injection
- **Maintain cryptographic integrity** - SHA-256 for evidence hashing
- **No secrets in code** - Use environment variables or AWS Secrets Manager

### Environment Variables

- `CUTOFF_DATE` - Date for IPE extraction (format: YYYY-MM-DD)
- `TEMPORAL_ADDRESS` - Temporal server address (default: localhost:7233)
- `AWS_PROFILE` - AWS profile name for credentials
- `AWS_REGION` - AWS region (default: eu-west-1)
- `S3_BUCKET_EVIDENCE` - S3 bucket for storing evidence packages
- `USE_OKTA_AUTH` - Enable Okta SSO authentication (true/false)

**Note**: Teleport tunnel (`tsh`) must be configured separately via `tsh login` before running extractions.

## Domain-Specific Knowledge

### IPE (Information Produced by the Entity)

IPEs are data extracts from business systems used as evidence for SOX compliance. Each IPE has:
- Unique ID (e.g., IPE_07, IPE_31)
- SQL query for extraction
- Critical columns for validation
- Validation rules (completeness, accuracy)

### Digital Evidence Package

Each extraction generates a package containing:
1. `ipe_data.csv` - Raw query results
2. `evidence.json` - Full audit metadata
3. `execution.log` - Detailed operation log
4. SHA-256 integrity hash

### Key IPEs in This Project

**Acronyms**: TV = Transaction Value, BOB = Buy Online/Backoffice, SC = Seller Center, PG = Payment Gateway

| IPE ID | Description |
|--------|-------------|
| IPE_07 | Customer balances - Monthly balances at cutoff date |
| IPE_08 | Store credit vouchers Transaction Value |
| IPE_09 | BOB (Buy Online/Backoffice) Sales Orders |
| IPE_11 | Seller Center Liability reconciliation |
| IPE_31 | Payment Gateway detailed Transaction Value extraction |

## Common Tasks

### Adding a New IPE

1. Add IPE definition to `src/core/catalog/cpg1.py`
2. Include SQL query, critical columns, and validation rules
3. Add corresponding test in `tests/`
4. Update IPE catalog documentation

### Modifying Temporal Workflows

1. Workflows are defined in `src/orchestrators/`
2. Activities are separate from workflow definitions
3. Test workflow changes with the Temporal test framework

### Working with Evidence System

1. Evidence manager is in `src/core/evidence/manager.py`
2. Always maintain cryptographic hash integrity
3. Evidence packages are stored in `evidence/` directory

## Review Checklist

When reviewing changes, verify:
- [ ] No hardcoded credentials or secrets
- [ ] SQL queries use parameterized inputs
- [ ] New functions have type hints and docstrings
- [ ] Tests are added for new functionality
- [ ] Code passes `black` and `flake8` checks
- [ ] Evidence integrity is maintained for any data operations
